from typing import Dict, Any, List, Optional
from src.preprocessing.cleaner import ClinicalTextCleaner
from src.nlp.entity_extractor import ClinicalEntityExtractor

class ClinicalSOAPGenerator:
    """
    Generates structured SOAP (Subjective, Objective, Assessment, Plan) notes 
    from clinical dialogue transcripts or raw narrative notes.
    """

    def __init__(self):
        self.cleaner = ClinicalTextCleaner()
        self.extractor = ClinicalEntityExtractor()

    def generate_soap_note(self, raw_text: str, patient_metadata: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """
        Generates a comprehensive SOAP note from the input clinical text/dialogue.
        """
        cleaned = self.cleaner.clean_text(raw_text)
        turns = self.cleaner.parse_dialogue_turns(raw_text)
        entities = self.extractor.extract_all(cleaned)

        # 1. Subjective Analysis
        subjective_points = []
        patient_utterances = [utt for spk, utt in turns if spk.lower() == 'patient']
        
        # Present symptoms
        present_symptoms = [s["entity"] for s in entities["symptoms"] if s["status"] == "Present"]
        absent_symptoms = [s["entity"] for s in entities["symptoms"] if s["status"] == "Absent/Negated"]

        if present_symptoms:
            subjective_points.append(f"**Chief Complaints & Symptoms**: Patient reports {', '.join(present_symptoms)}.")
        if absent_symptoms:
            subjective_points.append(f"**Pertinent Negatives**: Denies {', '.join(absent_symptoms)}.")
        if patient_utterances:
            subjective_points.append(f"**Patient Narrative**: \"{patient_utterances[0]}\"")
        elif not subjective_points:
            subjective_points.append("Patient presents for clinical evaluation.")

        # 2. Objective Analysis
        objective_points = []
        vitals = entities["vitals"]
        if vitals:
            vital_str = ", ".join([f"{k}: {v}" for k, v in vitals.items()])
            objective_points.append(f"**Vital Signs**: {vital_str}")
        else:
            objective_points.append("**Vital Signs**: Vital signs reviewed and documented in EHR.")

        # Doctor observations from turns
        doctor_utterances = [utt for spk, utt in turns if spk.lower() == 'doctor']
        exam_findings = []
        for utt in doctor_utterances:
            if any(term in utt.lower() for term in ["exam", "lung", "heart", "sound", "clear", "swelling", "abdomen", "regular", "murmur"]):
                exam_findings.append(utt)
        if exam_findings:
            objective_points.append(f"**Physical Exam Findings**: {'; '.join(exam_findings[:2])}")
        else:
            objective_points.append("**Physical Exam Findings**: Alert and oriented x3. General appearance consistent with history.")

        # 3. Assessment
        assessment_points = []
        diagnoses = [d["entity"] for d in entities["diagnoses"]]
        if diagnoses:
            assessment_points.append(f"**Primary Impression / Working Diagnoses**:\n" + "\n".join([f"- {d}" for d in diagnoses]))
        elif present_symptoms:
            assessment_points.append(f"**Clinical Impression**: Undifferentiated presentation consistent with {', '.join(present_symptoms)}.")
        else:
            assessment_points.append("**Clinical Impression**: General medical consultation; stable clinical status.")

        # 4. Plan
        plan_points = []
        meds = entities["medications"]
        if meds:
            med_list = [f"{m['medication']} ({m['dosage']})" for m in meds]
            plan_points.append(f"**Medication Management**: Continue/Prescribe {', '.join(med_list)}.")
        
        # Diagnostic & follow-up recommendations
        plan_points.append("**Diagnostics & Workup**: Monitor vital trends; routine laboratory workup as clinically indicated.")
        plan_points.append("**Follow-up & Patient Education**: Return to clinic in 1-2 weeks or immediately proceed to Emergency Department if red-flag symptoms develop.")

        # Compose output dict
        soap = {
            "metadata": patient_metadata or {},
            "raw_input_length": len(raw_text),
            "subjective": "\n\n".join(subjective_points),
            "objective": "\n\n".join(objective_points),
            "assessment": "\n\n".join(assessment_points),
            "plan": "\n\n".join(plan_points),
            "entities": entities
        }

        # Formatted markdown presentation
        soap["markdown_summary"] = (
            f"### CLINICAL SOAP NOTE\n\n"
            f"#### [S] Subjective\n{soap['subjective']}\n\n"
            f"#### [O] Objective\n{soap['objective']}\n\n"
            f"#### [A] Assessment\n{soap['assessment']}\n\n"
            f"#### [P] Plan\n{soap['plan']}"
        )

        return soap
