import re
from typing import Dict, List, Any

class ClinicalEntityExtractor:
    """
    Extracts key clinical entities including:
    - Symptoms and Chief Complaints with contextual negation scoping
    - Vital signs (BP, HR, SpO2, Temp, RR)
    - Diagnoses / Conditions
    - Medications and Dosages
    """

    NEGATION_TERMS = [
        r'\bno\b', r'\bdenies\b', r'\bnegative for\b', r'\bwithout\b',
        r'\bnot experiencing\b', r'\bruled out\b', r'\bdenied\b', r'\babsence of\b',
        r'\bnot having\b', r'\bhas not\b'
    ]

    SYMPTOM_DICTIONARY = [
        "chest pain", "chest tightness", "shortness of breath", "dyspnea",
        "palpitations", "dizziness", "lightheadedness", "fatigue", "nausea",
        "vomiting", "headache", "fever", "chills", "cough", "wheezing",
        "abdominal pain", "back pain", "swelling", "edema", "joint pain",
        "numbness", "tingling", "sweating", "diaphoresis", "sore throat",
        "congestion", "weight loss", "weight gain", "insomnia", "malaise"
    ]

    DIAGNOSIS_DICTIONARY = [
        "hypertension", "essential hypertension", "type 2 diabetes", "diabetes mellitus",
        "t2dm", "coronary artery disease", "cad", "atrial fibrillation", "a-fib",
        "asthma", "copd", "chronic obstructive pulmonary disease", "pneumonia",
        "hyperlipidemia", "dyslipidemia", "chronic kidney disease", "ckd",
        "gastroesophageal reflux disease", "gerd", "heart failure", "chf",
        "major depressive disorder", "anxiety disorder", "osteoarthritis"
    ]

    MEDICATION_PATTERNS = [
        r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\s+(\d+(?:\.\d+)?\s*(?:mg|mcg|g|ml|units?|tablets?|puffs?))\b',
        r'\b(lisinopril|metformin|atorvastatin|amlodipine|metoprolol|albuterol|levothyroxine|omeprazole|losartan|gabapentin|hydrochlorothiazide|furosemide|aspirin|ibuprofen|acetaminophen|amoxicillin|azithromycin|ciprofloxacin|prednisone|insulin|glipizide|sertraline|escitalopram)\b(?:\s+(\d+(?:\.\d+)?\s*(?:mg|mcg|g|ml|units?|puffs?)))?'
    ]

    VITAL_PATTERNS = {
        "Blood Pressure": r'(?:BP|Blood Pressure)(?:\s+(?:is|was|recorded|measured at|of)|[:\s])+\s*(\d{2,3}\s*/\s*\d{2,3})',
        "Heart Rate": r'(?:HR|Heart Rate|Pulse)(?:\s+(?:is|was|recorded|measured at|of)|[:\s])+\s*(\d{2,3})',
        "Respiratory Rate": r'(?:RR|Respiratory Rate)(?:\s+(?:is|was|recorded|measured at|of)|[:\s])+\s*(\d{1,2})',
        "SpO2 / Oxygen Saturation": r'(?:SpO2|Oxygen Saturation|O2 Sat|SpO2 is|O2 Saturation)(?:\s+(?:is|was|recorded|measured at|of)|[:\s])+\s*(\d{2,3})\s*%?',
        "Temperature": r'(?:Temp|Temperature)(?:\s+(?:is|was|recorded|measured at|of)|[:\s])+\s*(\d{2,3}(?:\.\d{1,2})?)'
    }

    def __init__(self):
        self.negation_regex = re.compile(r'|'.join(self.NEGATION_TERMS), re.IGNORECASE)

    def extract_vitals(self, text: str) -> Dict[str, str]:
        vitals = {}
        for vital_name, pattern in self.VITAL_PATTERNS.items():
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                vitals[vital_name] = match.group(1).strip()
        return vitals

    def split_into_clauses(self, text: str) -> List[str]:
        """Splits sentences into sub-clauses on sentence boundaries and conjunctions."""
        if not text:
            return []
        raw_parts = re.split(r'[.\n;]|\b(?:but|however|except|although|whereas)\b', text, flags=re.IGNORECASE)
        return [p.strip() for p in raw_parts if p and p.strip()]

    def is_negated_in_clause(self, clause: str, entity_span: str) -> bool:
        clause_lower = clause.lower()
        entity_lower = entity_span.lower()
        
        pos = clause_lower.find(entity_lower)
        if pos == -1:
            return False
            
        preceding_window = clause_lower[max(0, pos - 40):pos]
        if self.negation_regex.search(preceding_window):
            return True

        following_window = clause_lower[pos + len(entity_lower):min(len(clause_lower), pos + len(entity_lower) + 25)]
        if re.search(r'\b(?:absent|negative|denied|ruled out)\b', following_window):
            return True

        return False

    def extract_symptoms(self, text: str) -> List[Dict[str, Any]]:
        results = []
        clauses = self.split_into_clauses(text)

        present_set = set()
        negated_set = set()

        for clause in clauses:
            clause_lower = clause.lower()
            for symptom in self.SYMPTOM_DICTIONARY:
                if symptom in clause_lower:
                    negated = self.is_negated_in_clause(clause, symptom)
                    sym_title = symptom.title()
                    if negated:
                        negated_set.add(sym_title)
                    else:
                        present_set.add(sym_title)

        for sym in present_set:
            if sym not in negated_set:
                results.append({"entity": sym, "type": "Symptom/Finding", "status": "Present", "context": ""})
        for sym in negated_set:
            results.append({"entity": sym, "type": "Symptom/Finding", "status": "Absent/Negated", "context": ""})

        return results

    def extract_diagnoses(self, text: str) -> List[Dict[str, Any]]:
        results = []
        clauses = self.split_into_clauses(text)
        seen = set()

        for clause in clauses:
            clause_lower = clause.lower()
            for diag in self.DIAGNOSIS_DICTIONARY:
                if diag in clause_lower and diag not in seen:
                    seen.add(diag)
                    results.append({
                        "entity": diag.title(),
                        "type": "Condition/Diagnosis",
                        "context": clause.strip()
                    })
        return results

    def extract_medications(self, text: str) -> List[Dict[str, str]]:
        meds = []
        seen = set()

        for pattern in self.MEDICATION_PATTERNS:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                groups = [g for g in match.groups() if g]
                if groups:
                    med_name = groups[0].strip().title()
                    dosage = groups[1].strip() if len(groups) > 1 and groups[1] else "Not Specified"
                    key = f"{med_name}_{dosage}"
                    if key not in seen:
                        seen.add(key)
                        meds.append({
                            "medication": med_name,
                            "dosage": dosage,
                            "raw": match.group(0).strip()
                        })
        return meds

    def extract_all(self, text: str) -> Dict[str, Any]:
        return {
            "vitals": self.extract_vitals(text),
            "symptoms": self.extract_symptoms(text),
            "diagnoses": self.extract_diagnoses(text),
            "medications": self.extract_medications(text)
        }