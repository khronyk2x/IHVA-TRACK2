import unittest
import os
import shutil
import pandas as pd
from src.nlp.icd10_mapper import ICD10OntologyMapper
from src.nlp.organizer_extractor import OrganizerRecordExtractor
from src.database.registry import CentralClinicalRegistry
from src.ocr.image_scanner import ClinicalOCRScanner
from src.audio.transcriber import MultilingualClinicalAudioTranscriber

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

if __name__ == '__main__':
    unittest.main()