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
from src.utils.data_auditor import ClinicalDataAuditor

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


    def test_data_auditor_and_sorting(self):
        auditor = ClinicalDataAuditor()
        df_sample = pd.DataFrame([
            {
                "id": "T2_0001_V01", "source_encounter_id": "E0001", "variant_id": 1,
                "clinical_narrative": "Fever for 3 days. Exam: Temp 38.5 C. Diagnosed Malaria. Plan: ACT.",
                "chief_complaint": "Fever", "hpi": "Fever for 3 days", "pmh": "None", "exam": "Temp 38.5 C",
                "differential": "Malaria", "final_diagnosis": "Malaria", "icd10": "B54",
                "investigations": "Malaria RDT", "medications": "Artemether-Lumefantrine 80/480mg PO BID x 3 days",
                "treatment_plan": "Complete ACT", "soap_note": "S: Fever. O: Temp 38.5 C. A: Malaria. P: ACT."
            },
            {
                "id": "T2_0002_V01", "source_encounter_id": "E0002", "variant_id": 1,
                "clinical_narrative": "Patient coughing.",
                "chief_complaint": "", "hpi": "", "pmh": "", "exam": "HR 280",
                "differential": "", "final_diagnosis": "Asthma", "icd10": "I10",
                "investigations": "", "medications": "", "treatment_plan": "", "soap_note": ""
            }
        ])
        
        audit_res = auditor.audit_dataframe(df_sample)
        self.assertEqual(audit_res["total_records"], 2)
        self.assertEqual(audit_res["clean_records"], 1)
        self.assertEqual(audit_res["critical_records"], 1)

        # Test Sorting & Filtering
        filtered_df = auditor.sort_and_filter(audit_res["audited_df"], sort_by="Quality_Score", ascending=True)
        self.assertEqual(filtered_df.iloc[0]["id"], "T2_0002_V01")

        # Test Auto-rectification
        rectified_df = auditor.auto_rectify_dataframe(df_sample)
        self.assertEqual(len(rectified_df), 2)
        self.assertEqual(rectified_df.iloc[1]["icd10"], "J45.9")


    def test_deidentification_and_pediatric_plausibility(self):
        auditor = ClinicalDataAuditor()
        
        # Test Pediatric 5yo 90kg mismatch
        df_ped = pd.DataFrame([{
            "id": "T2_PED_01", "source_encounter_id": "E0991", "variant_id": 1,
            "patient_age": 5, "patient_gender": "Male",
            "clinical_narrative": "Child aged 5 years presenting with fever. Weight: 90kg.",
            "chief_complaint": "Fever", "hpi": "Fever for 2 days", "pmh": "None",
            "exam": "Weight 90kg", "differential": "Malaria", "final_diagnosis": "Malaria",
            "icd10": "B54", "investigations": "Malaria RDT",
            "medications": "Artemether-Lumefantrine 20/120mg PO", "treatment_plan": "Oral ACT",
            "soap_note": "S: Fever. O: Wt 90kg. A: Malaria. P: ACT."
        }])
        
        audit_res = auditor.audit_dataframe(df_ped)
        self.assertEqual(audit_res["critical_records"], 1)
        self.assertIn("Pediatric Weight Mismatch", audit_res["audited_df"].iloc[0]["Lapses_Detected"])

        # Test De-identification
        deid_df = auditor.deidentify_dataset(df_ped)
        self.assertIn("Anonymous Patient", deid_df.iloc[0]["patient_name"])

if __name__ == '__main__':
    unittest.main()