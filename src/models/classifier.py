from typing import List, Dict, Tuple, Optional, Any
import os
import pickle
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.naive_bayes import MultinomialNB
from sklearn.pipeline import Pipeline

class ClinicalNoteClassifier:
    """
    Classifies clinical notes into medical specialties or triage categories
    (e.g., Cardiology, Pulmonology, Endocrinology, Orthopedics, General Practice).
    """

    DEFAULT_TRAINING_DATA = [
        ("Patient presents with substernal crushing chest pressure radiating to left arm and jaw. BP 155/95, HR 102. History of CAD and angina.", "Cardiology"),
        ("Severe crushing chest pain on exertion with diaphoresis, palpitations, and elevated troponin. ECG shows ST elevations.", "Cardiology"),
        ("Acute shortness of breath, bilateral expiratory wheezing, productive cough with green sputum, dyspnea. SpO2 91%.", "Pulmonology"),
        ("Chronic cough for 3 weeks, history of asthma and COPD exacerbation with wheezing. Prescribed albuterol inhaler.", "Pulmonology"),
        ("Elevated fasting blood glucose of 240 mg/dL, HbA1c is 9.2%. Polyuria and polydipsia reported. Initiating Metformin 500mg.", "Endocrinology"),
        ("Type 2 diabetes mellitus routine review. Blood sugar logs show frequent morning spikes. Dose adjustment for insulin required.", "Endocrinology"),
        ("Patient slipped and twisted right ankle. Significant swelling and tenderness over lateral malleolus. X-ray ordered for fracture.", "Orthopedics"),
        ("Severe lower back pain radiating down right leg after lifting heavy boxes. Positive straight leg raise test.", "Orthopedics"),
        ("Mild headache, rhinorrhea, sore throat for 2 days. Afebrile, lungs clear. Prescribed supportive care.", "General Practice"),
        ("Annual wellness exam. Blood pressure normal, all review of systems unremarkable. Immunizations updated.", "General Practice")
    ]

    def __init__(self):
        self.pipeline = Pipeline([
            ('tfidf', TfidfVectorizer(ngram_range=(1, 2), stop_words='english', sublinear_tf=True)),
            ('clf', MultinomialNB(alpha=0.1))
        ])
        self.is_trained = False
        self.classes_ = []

    def train_baseline(self, custom_data: Optional[List[Tuple[str, str]]] = None):
        data = custom_data or self.DEFAULT_TRAINING_DATA
        texts, labels = zip(*data)
        self.pipeline.fit(texts, labels)
        self.is_trained = True
        self.classes_ = list(self.pipeline.classes_)

    def predict(self, text: str) -> Dict[str, Any]:
        if not self.is_trained:
            self.train_baseline()
            
        pred_label = self.pipeline.predict([text])[0]
        probabilities = self.pipeline.predict_proba([text])[0]
        
        prob_dict = {cls: float(prob) for cls, prob in zip(self.classes_, probabilities)}
        sorted_probs = dict(sorted(prob_dict.items(), key=lambda item: item[1], reverse=True))

        return {
            "predicted_specialty": pred_label,
            "confidence": float(max(probabilities)),
            "probabilities": sorted_probs
        }

    def save(self, file_path: str):
        with open(file_path, 'wb') as f:
            pickle.dump(self.pipeline, f)

    def load(self, file_path: str):
        with open(file_path, 'rb') as f:
            self.pipeline = pickle.load(f)
            self.is_trained = True
            self.classes_ = list(self.pipeline.classes_)
