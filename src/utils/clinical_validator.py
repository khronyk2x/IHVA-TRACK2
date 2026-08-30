import re
from typing import Dict, Any, List, Optional, Tuple

class ClinicalPlausibilityValidator:
    """
    Pediatric Growth, Biometric Consistency, Sex-Specific Diagnosis,
    and Age-Stratified Physiological Anomaly Validation Engine (WHO & CDC Aligned).
    """

    # Sex-specific diagnostic restrictions
    FEMALE_ONLY_DIAGNOSES = [
        "pre-eclampsia", "preeclampsia", "eclampsia", "ovarian cyst", "uterine fibroid",
        "cervical cancer", "pregnancy", "antenatal", "postpartum hemorrhage", "endometriosis"
    ]

    MALE_ONLY_DIAGNOSES = [
        "prostate cancer", "benign prostatic hyperplasia", "bph", "testicular torsion",
        "prostatitis", "epididymitis", "erectile dysfunction"
    ]

    # Age-specific diagnostic restrictions
    NEONATAL_ONLY_DIAGNOSES = [
        "neonatal sepsis", "neonatal jaundice", "infant respiratory distress syndrome", "meconium aspiration"
    ]

    GERIATRIC_OR_ADULT_ONLY = [
        "alzheimer", "dementia", "presbycusis", "parkinson", "macular degeneration"
    ]

    @staticmethod
    def extract_weight_and_height(narrative: str, exam: str) -> Tuple[Optional[float], Optional[float]]:
        """Extracts weight in kg and height in cm from clinical text."""
        combined = f"{narrative} {exam}"
        weight_kg = None
        height_cm = None

        # Weight match (e.g. "Weight: 90kg", "Wt 12 kg", "90 kg")
        w_match = re.search(r'(?:weight|wt|body\s+weight)\s*[:=\s]*([\d.]+)\s*(?:kg|kilos|kilograms)?', combined, re.IGNORECASE)
        if not w_match:
            w_match = re.search(r'\b(\d+(?:\.\d+)?)\s*(?:kg|kilos|kilograms)\b', combined, re.IGNORECASE)
        if w_match:
            try:
                weight_kg = float(w_match.group(1))
            except Exception:
                pass

        # Height match (e.g. "Height: 110 cm", "Ht 120cm", "1.65 m")
        h_match = re.search(r'(?:height|ht|stature)\s*[:=\s]*([\d.]+)\s*(?:cm|meters|m)?', combined, re.IGNORECASE)
        if h_match:
            try:
                val = float(h_match.group(1))
                height_cm = val * 100 if val < 3.0 else val
            except Exception:
                pass

        return weight_kg, height_cm

    def validate_record(self, record: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Validates demographic, biometric, sex-specific, and clinical consistency across a record.
        Returns a list of identified anomalies with severity and category.
        """
        anomalies = []
        
        narrative = str(record.get("clinical_narrative") or "")
        exam = str(record.get("exam") or "")
        diag = str(record.get("final_diagnosis") or "").lower()
        gender = str(record.get("patient_gender") or record.get("gender") or "").strip().lower()

        # Extract Age
        age = None
        if "patient_age" in record and record["patient_age"] is not None:
            try: age = float(record["patient_age"])
            except Exception: pass
        elif "age" in record and record["age"] is not None:
            try: age = float(record["age"])
            except Exception: pass
        else:
            age_m = re.search(r'\b(\d+)\s*(?:years?|yrs?|yo|months?|mo)\s+old\b', narrative, re.IGNORECASE)
            if age_m:
                try: age = float(age_m.group(1))
                except Exception: pass

        # Extract Weight and Height
        weight_kg, height_cm = self.extract_weight_and_height(narrative, exam)

        # 1. Pediatric Biometric & Growth Consistency Checks (WHO / CDC Standards)
        if age is not None and weight_kg is not None:
            if age <= 1 and weight_kg > 20:
                anomalies.append({
                    "category": "Biometric Mismatch",
                    "severity": "Critical",
                    "description": f"Pediatric Weight Mismatch: Infant aged {int(age)} yr with recorded weight {weight_kg}kg (Expected normal: 2.5 - 12kg)."
                })
            elif 1 < age <= 5 and weight_kg > 35:
                anomalies.append({
                    "category": "Biometric Mismatch",
                    "severity": "Critical",
                    "description": f"Pediatric Weight Mismatch: Child aged {int(age)} yrs with recorded weight {weight_kg}kg (Expected normal: 8 - 25kg; plausible max 35kg)."
                })
            elif 5 < age <= 12 and (weight_kg < 10 or weight_kg > 95):
                anomalies.append({
                    "category": "Biometric Mismatch",
                    "severity": "Critical",
                    "description": f"Pediatric Weight Mismatch: Child aged {int(age)} yrs with weight {weight_kg}kg outside plausible physiological range (15 - 75kg)."
                })
            elif age >= 18 and weight_kg < 20:
                anomalies.append({
                    "category": "Biometric Mismatch",
                    "severity": "Critical",
                    "description": f"Adult Severe Underweight / Data Error: Adult aged {int(age)} yrs with recorded weight {weight_kg}kg (<20kg)."
                })

        # 2. Height vs Age Checks
        if age is not None and height_cm is not None:
            if age <= 3 and height_cm > 130:
                anomalies.append({
                    "category": "Biometric Mismatch",
                    "severity": "Critical",
                    "description": f"Pediatric Stature Mismatch: Toddler aged {int(age)} yrs with recorded height {height_cm}cm (Expected normal: 50 - 100cm)."
                })

        # 3. Sex-Diagnosis Compatibility Checks
        if gender in ["male", "m"]:
            for f_diag in self.FEMALE_ONLY_DIAGNOSES:
                if f_diag in diag:
                    anomalies.append({
                        "category": "Sex-Diagnosis Incompatibility",
                        "severity": "Critical",
                        "description": f"Biological Inconsistency: Female-specific condition '{record.get('final_diagnosis')}' diagnosed in male patient."
                    })
        elif gender in ["female", "f"]:
            for m_diag in self.MALE_ONLY_DIAGNOSES:
                if m_diag in diag:
                    anomalies.append({
                        "category": "Sex-Diagnosis Incompatibility",
                        "severity": "Critical",
                        "description": f"Biological Inconsistency: Male-specific condition '{record.get('final_diagnosis')}' diagnosed in female patient."
                    })

        # 4. Age-Diagnosis Compatibility Checks
        if age is not None:
            if age > 1:
                for neo_diag in self.NEONATAL_ONLY_DIAGNOSES:
                    if neo_diag in diag:
                        anomalies.append({
                            "category": "Age-Diagnosis Incompatibility",
                            "severity": "Critical",
                            "description": f"Age Inconsistency: Neonatal condition '{record.get('final_diagnosis')}' diagnosed in {int(age)}-year-old patient."
                        })
            if age < 15:
                for ger_diag in self.GERIATRIC_OR_ADULT_ONLY:
                    if ger_diag in diag:
                        anomalies.append({
                            "category": "Age-Diagnosis Incompatibility",
                            "severity": "Warning",
                            "description": f"Age Warning: Adult-onset degenerative condition '{record.get('final_diagnosis')}' recorded for pediatric patient ({int(age)} yrs)."
                        })

        return anomalies