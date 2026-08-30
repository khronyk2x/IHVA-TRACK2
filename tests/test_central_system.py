import unittest
import os
import shutil
import pandas as pd
from src.nlp.icd10_mapper import ICD10OntologyMapper
from src.nlp.organizer_extractor import OrganizerRecordExtractor
from src.database.registry import CentralClinicalRegistry
from src.ocr.image_scanner import ClinicalOCRScanner
from src.audio.transcriber import MultilingualClinicalAudioTranscriber
from src.utils.exporter import ClinicalDocumentExporter

class TestCentralSystem(unittest.TestCase):

    def setUp(self):
        self.icd_mapper = ICD10OntologyMapper()
        self.extractor = OrganizerRecordExtractor()
        self.test_db_path = "/home/Onahi/Devdir/hack/data/registry/test_registry.db"
        self.registry = CentralClinicalRegistry(db_path=self.test_db_path)
        self.ocr_scanner = ClinicalOCRScanner()
        self.audio_transcriber = MultilingualClinicalAudioTranscriber()

    def tearDown(self):
        if os.path.exists(self.test_db_path):
            os.remove(self.test_db_path)

    def test_icd10_mapping(self):
        ast = self.icd_mapper.lookup_diagnosis("Asthma")
        self.assertIsNotNone(ast)
        self.assertEqual(ast["code"], "J45.9")

        mal = self.icd_mapper.map_from_narrative("Patient tested positive for Malaria with high fever.")
        self.assertEqual(mal["code"], "B54")

    def test_15_column_record_extraction(self):
        narrative = "Chief complaint: Difficulty breathing and wheezing. HPI: Difficulty breathing for 3 days. Exam: Vitals stable. Plan: Treat for Asthma with Salbutamol."
        rec = self.extractor.extract_record(narrative, encounter_id="E0001", variant_id=1)
        
        expected_keys = [
            "id", "source_encounter_id", "variant_id", "clinical_narrative",
            "chief_complaint", "hpi", "pmh", "exam", "differential",
            "final_diagnosis", "icd10", "investigations", "medications",
            "treatment_plan", "soap_note"
        ]
        for key in expected_keys:
            self.assertIn(key, rec)
        
        self.assertEqual(rec["source_encounter_id"], "E0001")
        self.assertEqual(rec["variant_id"], 1)
        self.assertEqual(rec["icd10"], "J45.9")

    def test_registry_submission_and_export(self):
        narrative1 = "Chief complaint: Severe fever and chills for 4 days. Tested positive for Malaria. Prescribed ACT."
        rec1 = self.registry.submit_report(narrative1, source_encounter_id="E0010", author_role="Triage Nurse")
        self.assertEqual(rec1["variant_id"], 1)

        narrative2 = "Seen in clinic: Fever and body aches for four days. Lab confirms Malaria. Starting ACT."
        rec2 = self.registry.submit_report(narrative2, source_encounter_id="E0010", author_role="Lab Tech")
        self.assertEqual(rec2["variant_id"], 2)

        df = self.registry.get_all_records_df()
        self.assertEqual(len(df), 2)
        self.assertEqual(df.iloc[0]["source_encounter_id"], "E0010")
        self.assertEqual(df.iloc[1]["variant_id"], 2)

    def test_hausa_clinical_translation(self):
        hausa = "Ina jin zazzabi da ciwon kai da ciwon kirji"
        res = self.audio_transcriber.translate_hausa_to_clinical_english(hausa)
        self.assertIn("fever", res["translated_english"])
        self.assertIn("headache", res["translated_english"])
        self.assertIn("chest pain", res["translated_english"])

    def test_fhir_and_pdf_export(self):
        self.registry.nurse_intake("E0999", "Ibrahim Musa", 42, "Male", {"BP": "130/85", "HR": "84", "Temp": "38.2 C"}, "Acute fever and headache", "Dr. Sarah Smith, MD", "Nurse Amina")
        card = self.registry.get_care_card("E0999")
        
        # FHIR Bundle validation
        bundle = ClinicalDocumentExporter.to_fhir_bundle(card)
        self.assertEqual(bundle["resourceType"], "Bundle")
        self.assertGreaterEqual(bundle["total"], 3)

        # PDF Care Card generation
        pdf_test_path = "/home/Onahi/Devdir/hack/data/registry/test_card.pdf"
        ClinicalDocumentExporter.generate_patient_pdf(card, pdf_test_path)
        self.assertTrue(os.path.exists(pdf_test_path))
        if os.path.exists(pdf_test_path):
            os.remove(pdf_test_path)

    def test_vitals_validation_and_merge(self):
        v_valid = {"BP": "120/80", "HR": "72", "Temp": "37.1 C", "SpO2": "98%"}
        res_valid = self.registry.validate_vitals(v_valid)
        self.assertTrue(res_valid["valid"])

        v_invalid = {"BP": "invalid_format", "HR": "320", "Temp": "55.0 C", "SpO2": "15%"}
        res_invalid = self.registry.validate_vitals(v_invalid)
        self.assertFalse(res_invalid["valid"])
        self.assertGreaterEqual(len(res_invalid["warnings"]), 3)

        # Duplicate merge test
        self.registry.nurse_intake("E0888", "Fatima Aliyu", 28, "Female", v_valid, "Asthma wheezing", "Dr. Sarah Smith, MD")
        self.registry.nurse_intake("E0889", "Fatima Aliyu", 28, "Female", v_valid, "Asthma wheezing", "Dr. Sarah Smith, MD")
        m_res = self.registry.merge_encounters("E0888", "E0889")
        self.assertTrue(m_res["success"])

if __name__ == '__main__':
    unittest.main()