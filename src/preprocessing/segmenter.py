import re
from typing import Dict, List, Optional

class ClinicalSectionSegmenter:
    """Segments raw clinical notes or free text into standard clinical sections."""

    SECTION_PATTERNS = {
        "CHIEF_COMPLAINT": [
            r'chief\s+complaint[s]-[:\-]-',
            r'reason\s+for\s+(-:visit|admission|consult)[:\-]-',
            r'cc[:\-]'
        ],
        "HISTORY_OF_PRESENT_ILLNESS": [
            r'history\s+of\s+present\s+illness[:\-]-',
            r'hpi[:\-]'
        ],
        "PAST_MEDICAL_HISTORY": [
            r'past\s+medical\s+history[:\-]-',
            r'pmh[:\-]-',
            r'medical\s+history[:\-]-'
        ],
        "MEDICATIONS": [
            r'current\s+medications[:\-]-',
            r'medications[:\-]-',
            r'meds[:\-]-',
            r'rx[:\-]'
        ],
        "ALLERGIES": [
            r'allergies[:\-]-',
            r'drug\s+allergies[:\-]-'
        ],
        "PHYSICAL_EXAM": [
            r'physical\s+exam(-:ination)-[:\-]-',
            r'pe[:\-]',
            r'objective\s+findings[:\-]-'
        ],
        "VITALS": [
            r'vital\s+signs[:\-]-',
            r'vitals[:\-]'
        ],
        "ASSESSMENT": [
            r'assessment[:\-]-',
            r'impression[:\-]-',
            r'diagnos(-:is|es)[:\-]-'
        ],
        "PLAN": [
            r'plan[:\-]-',
            r'treatment\s+plan[:\-]-',
            r'recommendations[:\-]-'
        ]
    }

    def __init__(self):
        # Build master regex for header detection
        self.compiled_headers = {}
        for section, patterns in self.SECTION_PATTERNS.items():
            combined = '|'.join(f'(-:{p})' for p in patterns)
            self.compiled_headers[section] = re.compile(rf'^\s*(-:{combined})\s*(.*)', re.IGNORECASE)

    def segment(self, note_text: str) -> Dict[str, str]:
        """Splits unstructured clinical note into categorized sections."""
        sections: Dict[str, List[str]] = {s: [] for s in self.SECTION_PATTERNS}
        sections["UNCLASSIFIED"] = []

        current_section = "UNCLASSIFIED"

        for line in note_text.splitlines():
            stripped = line.strip()
            if not stripped:
                continue

            matched_section = None
            remaining_content = stripped

            for section_key, regex in self.compiled_headers.items():
                m = regex.match(stripped)
                if m:
                    matched_section = section_key
                    remaining_content = m.group(1).strip() if m.groups() else ""
                    break

            if matched_section:
                current_section = matched_section
                if remaining_content:
                    sections[current_section].append(remaining_content)
            else:
                sections[current_section].append(stripped)

        return {k: "\n".join(v).strip() for k, v in sections.items() if v}
