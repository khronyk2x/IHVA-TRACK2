import os
import sys
import argparse
import json
import urllib.request
from typing import Dict, Any
import pandas as pd

DATA_RAW_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../data/raw'))
DATA_PROCESSED_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../data/processed'))

os.makedirs(DATA_RAW_DIR, exist_ok=True)
os.makedirs(DATA_PROCESSED_DIR, exist_ok=True)

MTSAMPLES_URL = "https://raw.githubusercontent.com/socd06/medical-nlp/master/data/mtsamples.csv"
MTS_DIALOG_BASE_URL = "https://raw.githubusercontent.com/abachaa/MTS-Dialog/main/Main-Dataset"

def download_file(url: str, dest_path: str) -> bool:
    """Downloads a file from a URL to dest_path with progress indication."""
    print(f"Downloading from: {url}")
    try:
        req = urllib.request.Request(
            url,
            headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        )
        with urllib.request.urlopen(req, timeout=30) as response, open(dest_path, 'wb') as out_file:
            data = response.read()
            out_file.write(data)
        print(f"Saved to: {dest_path} ({len(data) / 1024:.1f} KB)")
        return True
    except Exception as e:
        print(f"Error downloading {url}: {e}")
        return False

def fetch_mtsamples() -> pd.DataFrame:
    """Fetches and processes the MTSamples clinical transcription dataset (4,999 records)."""
    print("\n--- [1/3] Fetching MTSamples Clinical Transcriptions ---")
    dest_file = os.path.join(DATA_RAW_DIR, "mtsamples.csv")
    
    if not os.path.exists(dest_file):
        success = download_file(MTSAMPLES_URL, dest_file)
        if not success:
            print("Failed to download MTSamples.")
            return pd.DataFrame()
    else:
        print(f"Using cached file: {dest_file}")

    df = pd.read_csv(dest_file)
    print(f"Loaded {len(df)} records.")
    
    df_clean = df.dropna(subset=['transcription', 'medical_specialty']).copy()
    df_clean['transcription'] = df_clean['transcription'].str.strip()
    df_clean['medical_specialty'] = df_clean['medical_specialty'].str.strip()
    
    summary_path = os.path.join(DATA_PROCESSED_DIR, "mtsamples_processed.csv")
    df_clean.to_csv(summary_path, index=False)
    print(f"Processed dataset saved to: {summary_path}")
    print(f"Top 5 Specialties:\n{df_clean['medical_specialty'].value_counts().head(5)}")
    return df_clean

def fetch_mts_dialog() -> Dict[str, Any]:
    """Fetches the official NIH MTS-Dialog dataset for Clinical Dialogue to SOAP Note generation."""
    print("\n--- [2/3] Fetching MTS-Dialog (Clinical Dialogue to SOAP) ---")
    splits = {
        "train": (f"{MTS_DIALOG_BASE_URL}/MTS-Dialog-TrainingSet.csv", os.path.join(DATA_RAW_DIR, "mts_dialog_train.csv")),
        "validation": (f"{MTS_DIALOG_BASE_URL}/MTS-Dialog-ValidationSet.csv", os.path.join(DATA_RAW_DIR, "mts_dialog_valid.csv")),
        "test_chat": (f"{MTS_DIALOG_BASE_URL}/MTS-Dialog-TestSet-1-MEDIQA-Chat-2023.csv", os.path.join(DATA_RAW_DIR, "mts_dialog_test_chat.csv")),
        "test_sum": (f"{MTS_DIALOG_BASE_URL}/MTS-Dialog-TestSet-2-MEDIQA-Sum-2023.csv", os.path.join(DATA_RAW_DIR, "mts_dialog_test_sum.csv"))
    }

    all_data = {}
    for split_name, (url, path) in splits.items():
        if not os.path.exists(path):
            download_file(url, path)
        if os.path.exists(path):
            df = pd.read_csv(path)
            all_data[split_name] = df.to_dict(orient="records")
            print(f"{split_name} split loaded: {len(df)} dialogue-note pairs.")

    processed_path = os.path.join(DATA_PROCESSED_DIR, "mts_dialog_pairs.json")
    with open(processed_path, "w", encoding="utf-8") as f:
        json.dump(all_data, f, indent=2)
    print(f"MTS-Dialog processed JSON saved to: {processed_path}")
    return all_data

def generate_local_synthetic_fixtures():
    """Generates structured synthetic benchmark samples for immediate local offline testing."""
    print("\n--- [3/3] Generating Local Benchmark Fixtures ---")
    fixtures = [
        {
            "encounter_id": "ENC-001",
            "specialty": "Cardiology",
            "dialogue": "Doctor: How long have you had this chest tightness?\nPatient: For about 4 days, especially when walking up stairs.\nDoctor: BP is 150/95, HR is 88 bpm. We will start Lisinopril 10mg daily and order an ECG.",
            "target_soap": {
                "subjective": "Patient reports 4-day history of exertional chest tightness. Denies radiation.",
                "objective": "BP 150/95, HR 88 bpm. Regular rhythm.",
                "assessment": "Hypertension; exertional chest discomfort suspicious for angina.",
                "plan": "Initiate Lisinopril 10mg PO QD. Order 12-lead ECG and baseline troponins."
            }
        },
        {
            "encounter_id": "ENC-002",
            "specialty": "Pulmonology",
            "dialogue": "Doctor: Tell me about your breathing.\nPatient: I am wheezing a lot since yesterday and coughing up white phlegm.\nDoctor: SpO2 is 92%, Respiratory rate is 22 breaths/min. Lung exam shows bilateral wheezing.",
            "target_soap": {
                "subjective": "Acute dyspnea and wheezing with productive cough.",
                "objective": "SpO2 92%, RR 22. Bilateral expiratory wheezes.",
                "assessment": "Asthma exacerbation.",
                "plan": "Nebulized Albuterol stat. Prescribe Prednisone 40mg taper."
            }
        }
    ]

    fixture_path = os.path.join(DATA_PROCESSED_DIR, "clinical_benchmark_fixtures.json")
    with open(fixture_path, "w", encoding="utf-8") as f:
        json.dump(fixtures, f, indent=2)
    print(f"Benchmark fixtures saved to: {fixture_path}")

def main():
    parser = argparse.ArgumentParser(description="Fetch real open clinical datasets online.")
    parser.add_argument(
        "--dataset",
        choices=["all", "mtsamples", "dialogues", "fixtures"],
        default="all",
        help="Dataset to fetch (default: all)"
    )
    args = parser.parse_args()

    print("=" * 65)
    print("CLINICAL DATASET INGESTION PIPELINE (TRACK 2)")
    print("=" * 65)

    if args.dataset in ["all", "mtsamples"]:
        fetch_mtsamples()
    if args.dataset in ["all", "dialogues"]:
        fetch_mts_dialog()
    if args.dataset in ["all", "fixtures"]:
        generate_local_synthetic_fixtures()

    print("\n" + "=" * 65)
    print("Dataset ingestion complete. All data stored in data/raw/ and data/processed/")
    print("=" * 65)

if __name__ == "__main__":
    main()