import unittest
from src.preprocessing.cleaner import ClinicalTextCleaner
from src.preprocessing.segmenter import ClinicalSectionSegmenter
from src.nlp.entity_extractor import ClinicalEntityExtractor
from src.nlp.soap_generator import ClinicalSOAPGenerator
from src.models.classifier import ClinicalNoteClassifier
from src.utils.exporter import ClinicalDocumentExporter
from src.utils.metrics import ClinicalEvaluationMetrics

class TestClinicalPipeline(unittest.TestCase):

    def setUp(self):
        self.cleaner = ClinicalTextCleaner(expand_abbreviations=True)
        self.segmenter = ClinicalSectionSegmenter()
        self.extractor = ClinicalEntityExtractor()
        self.generator = ClinicalSOAPGenerator()
        self.classifier = ClinicalNoteClassifier()
        self.classifier.train_baseline()

    def test_cleaner_and_abbreviation(self):
        raw = "[10:45] Patient presents with SOB and elevated BP."
        cleaned = self.cleaner.clean_text(raw)
        self.assertNotIn("[10:45]", cleaned)
        self.assertIn("shortness of breath", cleaned)
        self.assertIn("Blood Pressure", cleaned)

    def test_entity_extractor_vitals(self):
        text = "BP: 130/85, HR: 82, SpO2: 97%"
        vitals = self.extractor.extract_vitals(text)
        self.assertEqual(vitals.get("Blood Pressure"), "130/85")
        self.assertEqual(vitals.get("Heart Rate"), "82")
        self.assertEqual(vitals.get("SpO2 / Oxygen Saturation"), "97")

    def test_entity_extractor_symptoms_and_negation(self):
        text = "Patient complains of chest tightness and palpitations, but denies cough and has no fever."
        symptoms = self.extractor.extract_symptoms(text)
        
        present = [s["entity"] for s in symptoms if s["status"] == "Present"]
        negated = [s["entity"] for s in symptoms if s["status"] == "Absent/Negated"]

        self.assertIn("Chest Tightness", present)
        self.assertIn("Palpitations", present)
        self.assertIn("Cough", negated)
        self.assertIn("Fever", negated)

    def test_medication_extraction(self):
        text = "Prescribing Metformin 500mg and Lisinopril 10mg."
        meds = self.extractor.extract_medications(text)
        med_names = [m["medication"] for m in meds]
        self.assertIn("Metformin", med_names)
        self.assertIn("Lisinopril", med_names)

    def test_soap_generation(self):
        dialogue = (
            "Doctor: How are you feeling?\n"
            "Patient: I have shortness of breath and wheezing.\n"
            "Doctor: BP is 120/80. Heart sound regular.\n"
            "Doctor: Start Albuterol 2 puffs."
        )
        soap = self.generator.generate_soap_note(dialogue)
        self.assertIn("subjective", soap)
        self.assertIn("objective", soap)
        self.assertIn("assessment", soap)
        self.assertIn("plan", soap)
        self.assertIn("Shortness Of Breath", soap["subjective"])

    def test_classifier_prediction(self):
        sample = "Patient with acute crushing substernal chest pain radiating to left arm and jaw."
        pred = self.classifier.predict(sample)
        self.assertEqual(pred["predicted_specialty"], "Cardiology")
        self.assertGreater(pred["confidence"], 0.4)

    def test_metrics_evaluation(self):
        ref = "Patient has acute bronchitis and mild cough"
        hyp = "Patient has bronchitis and severe cough"
        res = ClinicalEvaluationMetrics.calculate_token_f1(ref, hyp)
        self.assertGreater(res["f1"], 0.6)

if __name__ == '__main__':
    unittest.main()