from src.preprocessing.cleaner import ClinicalTextCleaner
from src.nlp.entity_extractor import ClinicalEntityExtractor
from src.nlp.soap_generator import ClinicalSOAPGenerator
from src.models.classifier import ClinicalNoteClassifier
from src.utils.sample_cases import SAMPLE_CASES
import json

def run_benchmark():
    print("=" * 60)
    print("MEDISCRIBE AI PIPELINE BENCHMARK")
    print("=" * 60)

    cleaner = ClinicalTextCleaner(expand_abbreviations=True)
    extractor = ClinicalEntityExtractor()
    generator = ClinicalSOAPGenerator()
    classifier = ClinicalNoteClassifier()
    classifier.train_baseline()

    for case_id, case_info in SAMPLE_CASES.items():
        print(f"\nEvaluating: {case_id}")
        text = case_info["text"]
        
        pred = classifier.predict(text)
        print(f"-> Predicted Specialty: {pred['predicted_specialty']} (Confidence: {pred['confidence']*100:.1f}%)")

        entities = extractor.extract_all(text)
        print(f"-> Vitals Detected: {len(entities['vitals'])} | Symptoms: {len(entities['symptoms'])} | Diagnoses: {len(entities['diagnoses'])} | Meds: {len(entities['medications'])}")
        
        soap = generator.generate_soap_note(text, patient_metadata=case_info["patient"])
        print("-> Generated SOAP Note Summary:")
        print(soap["markdown_summary"][:300] + "...\n")

if __name__ == '__main__':
    run_benchmark()
