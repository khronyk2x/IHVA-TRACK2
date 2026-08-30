import os
import json
import urllib.request
from typing import Dict, Any, Optional

class ClinicalLLMEngine:
    """
    Multi-backend Clinical LLM Engine:
    - Backend 1: Built-in Clinical NLP & Synthesis Engine (Fast, 100% Offline, Deterministic)
    - Backend 2: Local HuggingFace Transformer Pipeline (e.g., FLAN-T5, ClinicalBERT)
    - Backend 3: External API LLMs (OpenAI, Groq, Ollama, Anthropic compatible)
    """

    SYSTEM_PROMPT = """You are an expert Clinical AI Documentation Assistant.
Your task is to convert raw doctor-patient dialogues into standard clinical SOAP notes:
- Subjective (S): Chief complaints, symptoms, history of present illness, patient statements, pertinent negatives.
- Objective (O): Vital signs, physical examination findings, lab/imaging values.
- Assessment (A): Primary working diagnoses, clinical impressions, risk stratification.
- Plan (P): Medications (with dosages), diagnostic orders, therapies, follow-up schedule, and red-flag return precautions.
Maintain clinical accuracy and never hallucinate unmentioned medical details."""

    def __init__(self, backend: str = "clinical_nlp"):
        self.backend = backend

    def generate_with_api(self, prompt: str, api_key: str, api_base: str = "https://api.openai.com/v1", model: str = "gpt-4o-mini") -> Optional[str]:
        """Calls an OpenAI-compatible API (e.g. OpenAI, Groq, OpenRouter, Local Ollama)."""
        if not api_key:
            return None

        url = f"{api_base.rstrip('/')}/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"
        }

        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": self.SYSTEM_PROMPT},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.2,
            "max_tokens": 1000
        }

        try:
            req = urllib.request.Request(url, data=json.dumps(payload).encode('utf-8'), headers=headers)
            with urllib.request.urlopen(req, timeout=30) as resp:
                result = json.loads(resp.read().decode('utf-8'))
                return result["choices"][0]["message"]["content"]
        except Exception as e:
            print(f"API LLM Error: {e}")
            return None

    def generate_recommendations(self, entities: Dict[str, Any], specialty: str) -> Dict[str, Any]:
        """Generates clinical recommendations, differential checks, and red-flag alerts."""
        symptoms = [s["entity"].lower() for s in entities.get("symptoms", []) if s.get("status") == "Present"]
        diagnoses = [d["entity"].lower() for d in entities.get("diagnoses", [])]
        meds = entities.get("medications", [])
        vitals = entities.get("vitals", {})

        recommendations = []
        red_flags = []
        differentials = []

        # Cardiology / Chest pain checks
        if any(s in symptoms for s in ["chest pain", "chest tightness", "palpitations"]):
            recommendations.append("Order 12-lead Electrocardiogram (ECG) and baseline Troponin I / T enzymes.")
            recommendations.append("Assess cardiac risk factors (TIMI / HEART score).")
            differentials.extend(["Acute Coronary Syndrome (ACS)", "Stable / Unstable Angina", "Costochondritis", "Gastroesophageal Reflux"])
            red_flags.append("Diaphoresis, radiation to left arm or jaw, syncope, or hemodynamic instability.")

        # Respiratory / Asthma checks
        if any(s in symptoms for s in ["shortness of breath", "dyspnea", "wheezing", "cough"]):
            recommendations.append("Continuous pulse oximetry monitoring (maintain SpO2 >= 94%).")
            recommendations.append("Administer short-acting bronchodilator (Albuterol) with spacer or nebulizer.")
            differentials.extend(["Asthma Exacerbation", "COPD Exacerbation", "Community-Acquired Pneumonia", "Pulmonary Embolism"])
            red_flags.append("Inability to speak in full sentences, silent chest, cyanosis, accessory muscle use.")

        # Endocrinology / Diabetes checks
        if any("diabetes" in d for d in diagnoses) or any(s in symptoms for s in ["fatigue", "weight loss", "numbness"]):
            recommendations.append("Check HbA1c, fasting lipid panel, and comprehensive metabolic panel (CMP).")
            recommendations.append("Annual diabetic foot examination and dilated eye examination.")
            differentials.extend(["Type 2 Diabetes Mellitus with suboptimal control", "Diabetic Peripheral Neuropathy"])

        # Default clinical guidance if empty
        if not recommendations:
            recommendations.append("Continue current symptomatic management and monitor vital trends.")
            recommendations.append("Schedule standard clinical follow-up in 1-2 weeks.")

        if not differentials:
            differentials.append(f"{specialty} evaluation - clinical presentation under observation")

        return {
            "differentials": differentials[:4],
            "actionable_recommendations": recommendations,
            "red_flags": red_flags if red_flags else ["Sudden worsening of symptoms, high fever, or loss of consciousness."]
        }