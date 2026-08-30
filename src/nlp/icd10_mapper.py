import re
from typing import Dict, Tuple, Optional

ICD10_KNOWLEDGE_BASE: Dict[str, Dict[str, str]] = {
    "Malaria": {"code": "B54", "desc": "Unspecified malaria", "meds": "ACT", "investigations": "Malaria RDT; FBC"},
    "Diabetes Mellitus": {"code": "E11", "desc": "Type 2 diabetes mellitus", "meds": "Metformin", "investigations": "Random blood glucose; HbA1c"},
    "Type 2 Diabetes": {"code": "E11", "desc": "Type 2 diabetes mellitus", "meds": "Metformin", "investigations": "Random blood glucose; HbA1c"},
    "Hypertension": {"code": "I10", "desc": "Essential (primary) hypertension", "meds": "Amlodipine", "investigations": "BP monitoring; ECG; Urinalysis"},
    "Asthma": {"code": "J45.9", "desc": "Asthma, unspecified", "meds": "Salbutamol", "investigations": "Peak flow"},
    "Gastroenteritis": {"code": "A09", "desc": "Infectious gastroenteritis and colitis", "meds": "Oral rehydration salts; Zinc", "investigations": "Stool microscopy; Electrolytes"},
    "Tuberculosis": {"code": "A15.0", "desc": "Tuberculosis of lung", "meds": "TB regimen (Rifampicin/Isoniazid/Pyrazinamide/Ethambutol)", "investigations": "GeneXpert; Sputum AFB; CXR"},
    "Typhoid Fever": {"code": "A01.0", "desc": "Typhoid fever", "meds": "Ceftriaxone / Ciprofloxacin", "investigations": "Blood culture; Widal / FBC"},
    "Appendicitis": {"code": "K35.8", "desc": "Acute appendicitis, other and unspecified", "meds": "Surgical referral; IV Antibiotics", "investigations": "Abdominal Ultrasound; CBC"},
    "Epilepsy": {"code": "G40.9", "desc": "Epilepsy, unspecified", "meds": "Carbamazepine / Sodium Valproate", "investigations": "EEG; Neurology review; Brain MRI"},
    "Gout": {"code": "M10.9", "desc": "Gout, unspecified", "meds": "NSAIDs; Allopurinol", "investigations": "Serum uric acid; Joint X-ray"},
    "Dengue Fever": {"code": "A90", "desc": "Dengue fever", "meds": "Supportive care; Paracetamol; IV fluids", "investigations": "CBC; Dengue NS1 antigen / Serology"},
    "Pneumonia": {"code": "J18.9", "desc": "Pneumonia, unspecified organism", "meds": "Amoxicillin / Clavulanate", "investigations": "Chest X-ray; Sputum culture; CBC"},
    "Urinary Tract Infection": {"code": "N39.0", "desc": "Urinary tract infection, site not specified", "meds": "Nitrofurantoin / Ciprofloxacin", "investigations": "Urine microscopy, culture, and sensitivity (MCS)"},
    "Peptic Ulcer Disease": {"code": "K27", "desc": "Peptic ulcer, site unspecified", "meds": "Omeprazole; Clarithromycin; Amoxicillin", "investigations": "H. pylori stool antigen; Upper endoscopy"},
    "Anemia": {"code": "D64.9", "desc": "Anemia, unspecified", "meds": "Ferrous sulfate; Folic acid", "investigations": "FBC / Hemoglobin; Peripheral blood film"}
}

class ICD10OntologyMapper:
    """Maps clinical diagnoses and symptom clusters to standardized ICD-10 codes and standard care pathways."""

    def __init__(self):
        self.mapping = ICD10_KNOWLEDGE_BASE

    def lookup_diagnosis(self, query: str) -> Optional[Dict[str, str]]:
        if not query:
            return None
        
        query_clean = query.strip().lower()

        # Direct exact match
        for diag_name, info in self.mapping.items():
            if diag_name.lower() == query_clean:
                return {"diagnosis": diag_name, **info}

        # Substring / partial match
        for diag_name, info in self.mapping.items():
            if diag_name.lower() in query_clean or query_clean in diag_name.lower():
                return {"diagnosis": diag_name, **info}

        return None

    def map_from_narrative(self, narrative_text: str) -> Dict[str, str]:
        """Infers the most likely primary diagnosis and ICD-10 code from clinical narrative text."""
        text_lower = narrative_text.lower()

        best_match = None
        highest_score = 0

        for diag_name, info in self.mapping.items():
            score = 0
            # Direct condition name mention
            if diag_name.lower() in text_lower:
                score += 10
            # Code mention
            if info["code"].lower() in text_lower:
                score += 8
            # Medication mention
            if info["meds"].lower() in text_lower:
                score += 5
            # Investigation mention
            if any(term in text_lower for term in info["investigations"].lower().split(";")):
                score += 3

            if score > highest_score:
                highest_score = score
                best_match = {"diagnosis": diag_name, **info}

        if best_match:
            return best_match

        # Default fallback
        return {
            "diagnosis": "Clinical assessment pending",
            "code": "R69",
            "desc": "Illness, unspecified",
            "meds": "Supportive care",
            "investigations": "Clinical assessment; Routine laboratory evaluation"
        }