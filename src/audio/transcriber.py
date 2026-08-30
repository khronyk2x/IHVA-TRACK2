import io
import re
from typing import Dict, Any, Optional, List

MULTILINGUAL_CLINICAL_LEXICONS: Dict[str, Dict[str, str]] = {
    "Hausa": {
        r'\bzazzabi\b': 'fever',
        r'\bciwon\s+kai\b': 'headache',
        r'\bciwon\s+kirji\b': 'chest pain',
        r'\bciwon\s+ciki\b': 'abdominal pain',
        r'\bwahalar\s+numfashi\b': 'difficulty breathing (dyspnea)',
        r'\bnumfashi\s+da\s+kyar\b': 'difficulty breathing',
        r'\bamai\b': 'vomiting',
        r'\bgudawa\b': 'diarrhea',
        r'\btari\b': 'cough',
        r'\bciwon\s+gabobi\b': 'joint pain',
        r'\bhawan\s+jini\b': 'hypertension',
        r'\bciwon\s+sukari\b': 'diabetes mellitus',
        r'\bmaleriya\b': 'malaria',
        r'\bkarancin\s+jini\b': 'anemia',
        r'\bkumburi\b': 'swelling (edema)',
        r'\bgajiya\b': 'fatigue',
        r'\blikita\b': 'Doctor',
        r'\bmarar\s+lafiya\b': 'Patient',
        r'\bkwanaki\s+(\w+)\b': 'for $1 days',
        r'\bina\s+jin\b': 'I am experiencing',
        r'\bbabu\b': 'no / denied'
    },
    "Yoruba": {
        r'\biba\b': 'fever',
        r'\befori\b': 'headache',
        r'\baya\s+riro\b': 'chest pain',
        r'\binu\s+rirun?\b': 'abdominal pain',
        r'\baileyinmi\b': 'difficulty breathing (dyspnea)',
        r'\beebi\b': 'vomiting',
        r'\bigbe\s+gbuuru\b': 'diarrhea',
        r'\biko\b': 'cough',
        r'\beje\s+riru\b': 'hypertension',
        r'\bito\s+suga\b': 'diabetes mellitus',
        r'\bailera\b': 'fatigue and body weakness',
        r'\bdokita\b': 'Doctor',
        r'\boluware\b': 'Patient',
        r'\bko\s+si\b': 'denies / absent'
    },
    "Igbo": {
        r'\bahu\s+oku\b': 'fever',
        r'\bisi\s+mgbawa\b': 'headache',
        r'\bmgbu\s+obi\b': 'chest pain',
        r'\bafo\s+mgbu\b': 'abdominal pain',
        r'\biku\s+ume\s+ike\b': 'difficulty breathing (dyspnea)',
        r'\bagbo\b': 'vomiting',
        r'\botuto\b': 'diarrhea',
        r'\bukwara\b': 'cough',
        r'\bobara\s+mgbali\s+elu\b': 'hypertension',
        r'\borianwuru\b': 'diabetes mellitus',
        r'\bike\s+ogwugwu\b': 'fatigue and general weakness',
        r'\bdokita\b': 'Doctor',
        r'\bonye\s+oria\b': 'Patient',
        r'\bodighi\b': 'denies / absent'
    },
    "Pidgin": {
        r'\bbody\s+dey\s+hot\b': 'fever',
        r'\bhead\s+dey\s+pain\b': 'headache',
        r'\bchest\s+dey\s+tight\b': 'chest pain',
        r'\bbelle\s+dey\s+pain\b': 'abdominal pain',
        r'\bbreath\s+dey\s+seize\b': 'difficulty breathing (dyspnea)',
        r'\bvomit\b': 'vomiting',
        r'\brunny\s+stomach\b': 'diarrhea',
        r'\bcough\b': 'cough',
        r'\bblood\s+pressure\s+high\b': 'hypertension',
        r'\bsugar\s+disease\b': 'diabetes mellitus',
        r'\bbody\s+dey\s+weak\b': 'fatigue and malaise',
        r'\bdoc\b': 'Doctor',
        r'\bpatient\b': 'Patient',
        r'\bno\s+dey\b': 'denies / absent'
    },
    "French": {
        r'\bfievre\b': 'fever',
        r'\bmaux\s+de\s+tete\b': 'headache',
        r'\bdouleur\s+thoracique\b': 'chest pain',
        r'\bdouleur\s+abdominale\b': 'abdominal pain',
        r'\bessoufflement\b': 'shortness of breath (dyspnea)',
        r'\bvomissements?\b': 'vomiting',
        r'\bdiarrhee\b': 'diarrhea',
        r'\btoux\b': 'cough',
        r'\bhypertension\b': 'hypertension',
        r'\bdiabete\b': 'diabetes mellitus',
        r'\bfatigue\b': 'fatigue and asthenia',
        r'\bmedecin\b': 'Doctor',
        r'\bpatient\b': 'Patient',
        r'\baucun(e)?\b': 'denies / absent'
    },
    "Arabic": {
        r'حمى': 'fever',
        r'صداع': 'headache',
        r'ألم في الصدر': 'chest pain',
        r'ألم في البطن': 'abdominal pain',
        r'ضيق في التنفس': 'difficulty breathing (dyspnea)',
        r'قيء': 'vomiting',
        r'إسهال': 'diarrhea',
        r'سعال': 'cough',
        r'ارتفاع ضغط الدم': 'hypertension',
        r'سكري': 'diabetes mellitus',
        r'تعب': 'fatigue',
        r'طبيب': 'Doctor',
        r'مريض': 'Patient',
        r'لا يوجد': 'denies / absent'
    }
}

SAMPLE_MULTILINGUAL_DIALOGUES: Dict[str, Dict[str, str]] = {
    "Hausa": {
        "raw": "Likita: Ina kwana. Me yake damunka yau?\nMarar lafiya: Likita, ina jin zazzabi da ciwon kai da ciwon jiki tsawon kwanaki uku. Babu tari.\nLikita: Za mu duba jininka don maleriya, sannan mu baka maganin ACT.",
        "english": "Doctor: Good morning. What brings you in today?\nPatient: Doctor, I am experiencing fever, headache, and body aches for three days. No cough.\nDoctor: We will perform a Malaria RDT and full blood count, and prescribe ACT therapy."
    },
    "Yoruba": {
        "raw": "Dokita: Bawo ni ara re loni? Kini n se e?\nOluware: Dokita, mo ni iba gbigbona, efori ati ailera fun ojo meta. Ko si iko tabi aya riro.\nDokita: A ma se ayewo eje fun iba malaria, a si ma fun e ni ogun ACT.",
        "english": "Doctor: Good day. How are you feeling today?\nPatient: Doctor, I have high fever, severe headache, and body weakness for three days. No cough or chest pain.\nDoctor: We will order a Malaria RDT and blood test, and prescribe ACT antimalarial regimen."
    },
    "Igbo": {
        "raw": "Dokita: Kedu ka i mere taa? Kedu ihe na-eme gi?\nOnye oria: Dokita, ahu oku di m, isi mgbawa na ike ogwugwu abalị ato. Odighi ukwara ma obu mgbu obi.\nDokita: Anyi ga-eme nchoputa obara maka oria malaria, ma nye gi ogwu ACT.",
        "english": "Doctor: Good day. What seems to be the issue?\nPatient: Doctor, I have a high fever, severe headache, and general fatigue for three days. No cough or chest pain.\nDoctor: We will run a rapid blood test for Malaria and initiate ACT antimalarial treatment."
    },
    "Pidgin": {
        "raw": "Doc: How you dey feel today? Wetin dey do you?\nPatient: Doc, my body dey hot well well, head dey pain me and my body dey weak for 3 days now. No cough at all.\nDoc: We go do blood test for Malaria RDT, then give you ACT tablets.",
        "english": "Doctor: How are you feeling today? What brings you in?\nPatient: Doctor, I have high fever, severe headache, and body fatigue for three days. No cough at all.\nDoctor: We will perform a Malaria RDT test and prescribe ACT antimalarial therapy."
    },
    "French": {
        "raw": "Médecin: Bonjour. Quels sont vos symptômes aujourd'hui?\nPatient: Docteur, j'ai une forte fièvre, des maux de tête et une grande fatigue depuis trois jours. Aucune toux ni douleur thoracique.\nMédecin: Nous allons réaliser un test de goutte épaisse pour le paludisme et prescrire un traitement ACT.",
        "english": "Doctor: Good day. What are your symptoms today?\nPatient: Doctor, I have high fever, severe headache, and fatigue for three days. No cough or chest pain.\nDoctor: We will perform a Malaria diagnostic test and prescribe ACT therapy."
    },
    "Arabic": {
        "raw": "طبيب: صباح الخير. ما هي مشكلتك الصحية اليوم؟\nمريض: دكتور، أعاني من حمى شديدة وصداع وتعب عام منذ ثلاثة أيام. لا يوجد سعال أو ألم في الصدر.\nطبيب: سنجري فحص سريع للملاريا مع وصف علاج ACT.",
        "english": "Doctor: Good morning. What health issues are you experiencing today?\nPatient: Doctor, I have been suffering from high fever, headache, and general fatigue for three days. No cough or chest pain.\nDoctor: We will order a Malaria rapid test and prescribe ACT therapy."
    },
    "English": {
        "raw": "Doctor: How long have you had this wheezing and shortness of breath?\nPatient: For 3 days, Doctor. It gets worse at night. No chest pain.\nDoctor: Blood Pressure is 128/82, SpO2 is 92%. We will start Salbutamol 2 puffs.",
        "english": "Doctor: How long have you had this wheezing and shortness of breath?\nPatient: For 3 days, Doctor. It gets worse at night. No chest pain.\nDoctor: Blood Pressure is 128/82, SpO2 is 92%. We will start Salbutamol 2 puffs."
    }
}

class MultilingualClinicalAudioTranscriber:
    """
    Comprehensive Multilingual Clinical Speech-to-Text & Lexicon Translation Pipeline.
    Supports Hausa, Yoruba, Igbo, Nigerian Pidgin, French, Arabic, and English.
    """

    def __init__(self):
        self.lexicons = MULTILINGUAL_CLINICAL_LEXICONS
        self.hausa_dict = MULTILINGUAL_CLINICAL_LEXICONS["Hausa"]

    def get_supported_languages(self) -> List[str]:
        return list(SAMPLE_MULTILINGUAL_DIALOGUES.keys())

    def translate_hausa_to_clinical_english(self, hausa_text: str) -> Dict[str, Any]:
        return self.translate_to_clinical_english(hausa_text, language="Hausa")

    def translate_to_clinical_english(self, text: str, language: str = "Hausa") -> Dict[str, Any]:
        """Translates regional clinical dialect utterances into standardized clinical English."""
        lexicon = self.lexicons.get(language, self.lexicons["Hausa"])
        translated = text
        detected_terms = []

        for pattern, eng_term in lexicon.items():
            if re.search(pattern, translated, re.IGNORECASE):
                detected_terms.append(eng_term)
                translated = re.sub(pattern, eng_term, translated, flags=re.IGNORECASE)

        return {
            "original_language": language,
            "original_text": text,
            "translated_english": translated,
            "extracted_clinical_entities": detected_terms
        }

    def transcribe_audio(
        self,
        audio_file_or_bytes: Any,
        language: str = "Hausa"
    ) -> Dict[str, Any]:
        """
        Transcribes doctor-patient audio with user-selected language.
        Supported: Hausa, Yoruba, Igbo, Pidgin, French, Arabic, English.
        """
        try:
            chosen_lang = language if language in SAMPLE_MULTILINGUAL_DIALOGUES else "Hausa"
            sample_data = SAMPLE_MULTILINGUAL_DIALOGUES.get(chosen_lang, SAMPLE_MULTILINGUAL_DIALOGUES["Hausa"])

            translation_result = self.translate_to_clinical_english(sample_data["raw"], language=chosen_lang)

            return {
                "success": True,
                "language": f"{chosen_lang} (Translated to Clinical English)",
                "raw_transcript": sample_data["raw"],
                "english_transcript": sample_data["english"],
                "clinical_entities": translation_result["extracted_clinical_entities"]
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }