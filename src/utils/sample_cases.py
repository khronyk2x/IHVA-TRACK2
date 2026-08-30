"""
Sample clinical dialogue transcripts and notes for testing, demonstration, and evaluation.
"""

SAMPLE_CASES = {
    "Case 1: Cardiology Consult (Chest Pain & HTN)": {
        "title": "Cardiology Consult - Chest Pain",
        "specialty": "Cardiology",
        "patient": {"name": "Robert Miller", "age": 58, "gender": "Male", "mrn": "MRN-90214"},
        "text": """Doctor: Good morning Mr. Miller. What brings you in to see us today-
Patient: Good morning Doctor. Over the last 3 days, I've had this nagging chest tightness and shortness of breath when climbing the stairs.
Doctor: I see. Are you having any dizziness, palpitations, or pain radiating to your left arm or jaw-
Patient: No arm pain and no dizziness, but I definitely felt some palpitations yesterday afternoon.
Doctor: Any fever, cough, or nausea-
Patient: No fever and no cough at all.
Doctor: Let's check your vitals. Your Blood Pressure is 148/92 mmHg, and Heart Rate is 88 bpm. Respiratory Rate is 16 breaths/min. Oxygen Saturation is 98%.
Doctor: Your lungs sound completely clear on auscultation. Heart rhythm is regular with no murmurs detected.
Doctor: Are you currently taking any prescription medications-
Patient: Yes, I take Lisinopril 10mg once daily for my hypertension, but I admit I missed a couple of doses last week.
Doctor: Alright. Given your history of hypertension and recent chest tightness on exertion, we will order an Electrocardiogram and troponin lab panel, and increase your Lisinopril to 20mg daily.
Patient: Thank you Doctor. When should I follow up-
Doctor: Follow up in 1 week. If the chest pain becomes severe or radiates, go directly to the emergency department."""
    },

    "Case 2: Emergency / Pulmonology (Asthma Exacerbation)": {
        "title": "ER Acute Respiratory - Asthma",
        "specialty": "Pulmonology",
        "patient": {"name": "Sarah Jenkins", "age": 32, "gender": "Female", "mrn": "MRN-48102"},
        "text": """Doctor: Hello Sarah, what happened today-
Patient: Doctor, I can barely catch my breath. I started wheezing heavily this morning after being exposed to dust.
Doctor: Are you having chest pain or fever-
Patient: No chest pain and no fever, just extreme shortness of breath and wheezing.
Doctor: Checking your vitals right now: Blood Pressure is 124/80, Heart Rate is 110 bpm, Respiratory Rate is 24 breaths/min, and Oxygen Saturation is 91%.
Doctor: On physical exam, there is diffuse bilateral expiratory wheezing throughout all lung fields.
Doctor: What asthma medications do you usually take-
Patient: I take Albuterol 2 puffs as needed, but it didn't relieve it today.
Doctor: We will administer a nebulized Albuterol treatment immediately and initiate Prednisone 40mg for 5 days. We'll observe you until SpO2 stabilizes above 95%."""
    },

    "Case 3: Primary Care / Endocrinology (Type 2 Diabetes Review)": {
        "title": "Primary Care - Diabetes & Hyperlipidemia",
        "specialty": "Endocrinology",
        "patient": {"name": "David Garcia", "age": 52, "gender": "Male", "mrn": "MRN-33190"},
        "text": """Doctor: Hello David, good to see you for your routine diabetes follow-up.
Patient: Hi Dr. Evans. I've been feeling mostly okay, but experiencing some mild fatigue and increased thirst lately.
Doctor: Any numbness or tingling in your feet, or changes in your vision-
Patient: No numbness and no vision problems.
Doctor: Vital signs today: Blood Pressure is 132/84, Heart Rate is 74 bpm, Weight 92 kg.
Doctor: Your recent lab work shows HbA1c is 8.4% and fasting glucose was 175 mg/dL.
Doctor: Let's review your medications. You are on Metformin 500mg twice daily and Atorvastatin 20mg at bedtime.
Doctor: We are going to increase your Metformin to 1000mg twice daily to improve glycemic control. Continue Atorvastatin 20mg. We will recheck your HbA1c in 3 months."""
    }
}
