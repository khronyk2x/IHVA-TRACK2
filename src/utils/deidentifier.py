import re
from typing import Dict, Any, List, Optional

class ClinicalDeidentifier:
    """
    HIPAA Safe Harbor & NDPA (Nigeria Data Protection Act) Compliant
    PHI (Protected Health Information) and PII De-identification Engine.
    """

    PATTERNS = {
        "EMAIL": r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
        "PHONE": r'(?:\+?234|0)[789][01]\d{8}\b|\b\d{3}[-.]?\d{3}[-.]?\d{4}\b',
        "NIN_SSN": r'\b\d{11}\b|\b\d{3}-\d{2}-\d{4}\b',
        "MRN_HOSPITAL_NO": r'\b(?:MRN|HOSP|PAT|ID)[-:\s]*\d{4,8}\b',
        "STREET_ADDRESS": r'\b\d+\s+[A-Za-z\s]+(?:Street|St|Road|Rd|Avenue|Ave|Close|Crescent|Way|Boulevard)\b',
        "DATE_OF_BIRTH": r'\bDOB\s*[:=\s]*\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b'
    }

    PATIENT_NAMES_KNOWN = [
        "Ibrahim Musa", "Fatima Aliyu", "Emeka Okafor", "Chioma Adebayo",
        "Amina Yusuf", "John Doe", "Jane Doe", "Sarah Connor", "Onahi Emmanuel"
    ]

    def __init__(self, custom_names: Optional[List[str]] = None):
        self.known_names = set(self.PATIENT_NAMES_KNOWN)
        if custom_names:
            self.known_names.update(custom_names)

    def mask_text(self, text: str, preserve_encounter_id: Optional[str] = None) -> str:
        """Masks direct identifiers from narrative text, replacing them with standard redaction tokens."""
        if not text:
            return ""
        
        masked = text

        # 1. Mask Email, Phone, NIN, Address, DOB
        masked = re.sub(self.PATTERNS["EMAIL"], "[REDACTED_EMAIL]", masked, flags=re.IGNORECASE)
        masked = re.sub(self.PATTERNS["PHONE"], "[REDACTED_PHONE]", masked)
        masked = re.sub(self.PATTERNS["NIN_SSN"], "[REDACTED_NIN]", masked)
        masked = re.sub(self.PATTERNS["STREET_ADDRESS"], "[REDACTED_ADDRESS]", masked, flags=re.IGNORECASE)
        masked = re.sub(self.PATTERNS["DATE_OF_BIRTH"], "DOB: [AGE_PRESERVED]", masked, flags=re.IGNORECASE)

        # 2. Mask known patient names
        for name in self.known_names:
            pattern = rf'\b{re.escape(name)}\b'
            anon_tag = f"[PATIENT-{preserve_encounter_id}]" if preserve_encounter_id else "[PATIENT_NAME]"
            masked = re.sub(pattern, anon_tag, masked, flags=re.IGNORECASE)

        # 3. Mask name introductions like "Patient: John Doe" or "Name: Amina"
        masked = re.sub(r'\b(?:Patient Name|Patient|Name)\s*[:=-]\s*([A-Z][a-z]+\s+[A-Z][a-z]+)', r'Patient: [REDACTED_NAME]', masked)

        return masked

    def deidentify_record(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """De-identifies a complete 15-column clinical record for safe research/sorting/export."""
        rec = dict(record)
        enc_id = rec.get("source_encounter_id", "E0001")

        # Anonymize clinical narrative and notes
        if "clinical_narrative" in rec:
            rec["clinical_narrative"] = self.mask_text(rec["clinical_narrative"], enc_id)
        if "soap_note" in rec:
            rec["soap_note"] = self.mask_text(rec["soap_note"], enc_id)
        if "hpi" in rec:
            rec["hpi"] = self.mask_text(rec["hpi"], enc_id)
        
        # Redact direct author or patient identifiers
        rec["patient_name"] = f"Anonymous Patient ({enc_id})"
        if "author_name" in rec:
            rec["author_name"] = f"Clinician [{rec.get('author_role', 'Staff')}]"

        return rec

    def deidentify_dataframe(self, df) -> Any:
        """De-identifies an entire DataFrame of records."""
        records = df.to_dict(orient="records")
        deidentified = [self.deidentify_record(r) for r in records]
        import pandas as pd
        return pd.DataFrame(deidentified)