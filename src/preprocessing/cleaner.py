import re
from typing import Dict, List, Tuple

CLINICAL_ABBREVIATIONS: Dict[str, str] = {
    r'\bBP\b': 'Blood Pressure',
    r'\bHR\b': 'Heart Rate',
    r'\bRR\b': 'Respiratory Rate',
    r'\bSOB\b': 'shortness of breath',
    r'\bHTN\b': 'hypertension',
    r'\bDM2\b': 'Type 2 Diabetes Mellitus',
    r'\bT2D\b': 'Type 2 Diabetes',
    r'\bCAD\b': 'coronary artery disease',
    r'\bCXR\b': 'chest x-ray',
    r'\bECG\b': 'electrocardiogram',
    r'\bEKG\b': 'electrocardiogram',
    r'\bBID\b': 'twice daily',
    r'\bTID\b': 'three times daily',
    r'\bQID\b': 'four times daily',
    r'\bPRN\b': 'as needed',
    r'\bPO\b': 'orally',
    r'\bNPO\b': 'nothing by mouth',
    r'\bQD\b': 'every day',
    r'\bQHS\b': 'at bedtime',
    r'\bWNL\b': 'within normal limits',
    r'\bNKDA\b': 'no known drug allergies',
    r'\bHx\b': 'history',
    r'\bSx\b': 'symptoms',
    r'\bTx\b': 'treatment',
    r'\bDx\b': 'diagnosis',
    r'\bRx\b': 'prescription'
}

class ClinicalTextCleaner:
    """Utility class to clean, standardize, and normalize clinical transcripts and notes."""
    
    def __init__(self, expand_abbreviations: bool = False):
        self.expand_abbreviations = expand_abbreviations

    def clean_text(self, text: str) -> str:
        """Basic sanitization: clean whitespace, timestamps, and artifacts."""
        if not text:
            return ""
        
        cleaned = re.sub(r'\[?\b\d{1,2}:\d{2}(?::\d{2})?\b\]?', '', text)
        cleaned = re.sub(r'[\r\t]+', ' ', cleaned)
        cleaned = re.sub(r'[ ]{2,}', ' ', cleaned)
        
        lines = [line.strip() for line in cleaned.splitlines() if line.strip()]
        cleaned = '\n'.join(lines)
        
        if self.expand_abbreviations:
            cleaned = self.expand_medical_abbreviations(cleaned)
            
        return cleaned

    def expand_medical_abbreviations(self, text: str) -> str:
        """Expands common clinical abbreviations."""
        expanded = text
        for pattern, replacement in CLINICAL_ABBREVIATIONS.items():
            expanded = re.sub(pattern, replacement, expanded)
        return expanded

    def parse_dialogue_turns(self, transcript: str) -> List[Tuple[str, str]]:
        """Parses transcripts with speaker tags (Doctor, Patient, etc.)."""
        turns = []
        speaker_pattern = re.compile(r'^(Doctor|Clinician|Physician|Dr\.|Patient|Nurse|Caregiver):\s*(.*)', re.IGNORECASE)
        current_speaker = "Unknown"
        current_text = []

        for line in transcript.splitlines():
            line = line.strip()
            if not line:
                continue
            
            match = speaker_pattern.match(line)
            if match:
                if current_text:
                    turns.append((current_speaker, " ".join(current_text)))
                    current_text = []
                current_speaker = match.group(1).capitalize()
                if "Dr" in current_speaker or "Clinician" in current_speaker or "Physician" in current_speaker:
                    current_speaker = "Doctor"
                current_text.append(match.group(2))
            else:
                current_text.append(line)

        if current_text:
            turns.append((current_speaker, " ".join(current_text)))

        return turns