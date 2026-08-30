import re
from typing import Dict, Any, Optional
from src.preprocessing.cleaner import ClinicalTextCleaner
from src.nlp.entity_extractor import ClinicalEntityExtractor
from src.nlp.icd10_mapper import ICD10OntologyMapper

class OrganizerRecordExtractor:
    """
    Auto-extracts the official 15-column schema matching the hackathon organizer dataset:
    [id, source_encounter_id, variant_id, clinical_narrative, chief_complaint, 
     hpi, pmh, exam, differential, final_diagnosis, icd10, investigations, 
     medications, treatment_plan, soap_note]
    """

    def __init__(self):
        self.cleaner = ClinicalTextCleaner(expand_abbreviations=True)
        self.entity_extractor = ClinicalEntityExtractor()
        self.icd_mapper = ICD10OntologyMapper()

    def extract_record(
        self,
        clinical_narrative: str,
        encounter_id: str = "E0001",
        variant_id: int = 1,
        record_id: Optional[str] = None
    ) -> Dict[str, Any]:
        cleaned = self.cleaner.clean_text(clinical_narrative)
        rec_id = record_id or f"T2_{encounter_id.replace('E', '')}_{str(variant_id).zfill(2)}"

        # 1. Chief Complaint (CC)
        cc_match = re.search(r'(?:Chief\s+complaint|CC|Reason\s+for\s+visit)[:\s\-]+([^.\n]+)', clinical_narrative, re.IGNORECASE)
        if cc_match:
            chief_complaint = cc_match.group(1).strip()
        else:
            # Infer from first sentence or present symptoms
            symptoms = self.entity_extractor.extract_symptoms(cleaned)
            present_syms = [s["entity"] for s in symptoms if s["status"] == "Present"]
            chief_complaint = ", ".join(present_syms) if present_syms else "Patient presents for medical evaluation"

        # 2. History of Present Illness (HPI)
        hpi_match = re.search(r'(?:HPI|History\s+of\s+present\s+illness)[:\s\-]+([^.\n]+(?:\.[^.\n]+)?)', clinical_narrative, re.IGNORECASE)
        if hpi_match:
            hpi = hpi_match.group(1).strip()
        else:
            hpi = f"{chief_complaint} reported by patient."

        # 3. Past Medical History (PMH)
        pmh_match = re.search(r'(?:PMH|PMHx|Past\s+history|Past\s+medical\s+history)[:\s\-]+([^.\n]+)', clinical_narrative, re.IGNORECASE)
        if pmh_match:
            pmh = pmh_match.group(1).strip()
        else:
            diagnoses = self.entity_extractor.extract_diagnoses(cleaned)
            pmh = ", ".join([d["entity"] for d in diagnoses]) if diagnoses else "None reported"

        # 4. Physical Exam Findings
        exam_match = re.search(r'(?:Examination|Exam\s+findings|On\s+examination|PE)[:\s\-]+([^.\n]+)', clinical_narrative, re.IGNORECASE)
        if exam_match:
            exam = exam_match.group(1).strip()
        else:
            vitals = self.entity_extractor.extract_vitals(cleaned)
            if vitals:
                exam = ", ".join([f"{k}: {v}" for k, v in vitals.items()])
            else:
                exam = "Vitals stable"

        # 5. Diagnosis & ICD-10 Mapping
        icd_info = self.icd_mapper.map_from_narrative(clinical_narrative)
        final_diagnosis = icd_info["diagnosis"]
        icd10_code = icd_info["code"]
        differential = f"Suspected {final_diagnosis}; consider related clinical etiologies"

        # 6. Investigations
        inv_match = re.search(r'(?:Investigations\s+considered/documented|Investigations|Tests\s+ordered)[:\s\-]+([^.\n]+)', clinical_narrative, re.IGNORECASE)
        if inv_match:
            investigations = inv_match.group(1).strip()
        else:
            investigations = icd_info.get("investigations", "Routine baseline labs")

        # 7. Medications
        med_match = re.search(r'(?:Medications|Prescription|Rx|Meds)[:\s\-]+([^.\n]+)', clinical_narrative, re.IGNORECASE)
        if med_match:
            medications = med_match.group(1).strip()
        else:
            extracted_meds = self.entity_extractor.extract_medications(cleaned)
            if extracted_meds:
                medications = ", ".join([f"{m['medication']} {m['dosage']}" for m in extracted_meds])
            else:
                medications = icd_info.get("meds", "Supportive care")

        # 8. Treatment Plan
        plan_match = re.search(r'(?:Plan|Treatment\s+plan|Management)[:\s\-]+([^.\n]+)', clinical_narrative, re.IGNORECASE)
        if plan_match:
            treatment_plan = plan_match.group(1).strip()
        else:
            treatment_plan = f"Treat for {final_diagnosis}"

        # 9. Canonical SOAP Note string
        soap_note = f"S: {chief_complaint}. O: {exam}. A: Suspected {final_diagnosis}. P: {investigations}; {medications}."

        return {
            "id": rec_id,
            "source_encounter_id": encounter_id,
            "variant_id": variant_id,
            "clinical_narrative": clinical_narrative.strip(),
            "chief_complaint": chief_complaint,
            "hpi": hpi,
            "pmh": pmh,
            "exam": exam,
            "differential": differential,
            "final_diagnosis": final_diagnosis,
            "icd10": icd10_code,
            "investigations": investigations,
            "medications": medications,
            "treatment_plan": treatment_plan,
            "soap_note": soap_note
        }