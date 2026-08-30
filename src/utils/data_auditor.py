from src.utils.clinical_validator import ClinicalPlausibilityValidator
from src.utils.deidentifier import ClinicalDeidentifier
import re
import pandas as pd
import numpy as np
from typing import Dict, Any, List, Optional
from src.nlp.icd10_mapper import ICD10OntologyMapper
from src.nlp.organizer_extractor import OrganizerRecordExtractor
from src.preprocessing.cleaner import ClinicalTextCleaner

class ClinicalDataAuditor:
    """
    Comprehensive Data Quality, Anomaly Detection, Lapse Auditing,
    and Sorting Engine for Clinical Datasets and CSV Ingestions.
    """

    def __init__(self):
        self.icd_mapper = ICD10OntologyMapper()
        self.extractor = OrganizerRecordExtractor()
        self.cleaner = ClinicalTextCleaner(expand_abbreviations=True)
        self.plausibility_validator = ClinicalPlausibilityValidator()
        self.deidentifier = ClinicalDeidentifier()

    def audit_record(self, row: Dict[str, Any]) -> Dict[str, Any]:
        """Audits a single clinical record for data quality lapses, coding errors, and missing fields."""
        lapses = []
        severity = "Clean"
        score = 100

        narrative = str(row.get("clinical_narrative") or "")
        cc = str(row.get("chief_complaint") or "").strip()
        hpi = str(row.get("hpi") or "").strip()
        exam = str(row.get("exam") or "").strip()
        diag = str(row.get("final_diagnosis") or "").strip()
        icd = str(row.get("icd10") or "").strip()
        inv = str(row.get("investigations") or "").strip()
        meds = str(row.get("medications") or "").strip()
        plan = str(row.get("treatment_plan") or "").strip()
        soap = str(row.get("soap_note") or "").strip()

        # 1. Missing Required Clinical Fields
        if not cc or cc.lower() in ["none", "nan", "unspecified", ""]:
            lapses.append("Missing Chief Complaint (CC)")
            score -= 15
        if not hpi or hpi.lower() in ["none", "nan", ""]:
            lapses.append("Missing History of Present Illness (HPI)")
            score -= 15
        if not exam or exam.lower() in ["none", "nan", ""]:
            lapses.append("Missing Physical Exam & Vital Signs")
            score -= 15
        if not diag or diag.lower() in ["none", "nan", ""]:
            lapses.append("Missing Primary Diagnosis")
            score -= 20
        if not icd or icd.lower() in ["none", "nan", "r69", ""]:
            lapses.append("Uncoded or Generic ICD-10 Code")
            score -= 10
        if not inv or inv.lower() in ["none", "nan", ""]:
            lapses.append("Missing Diagnostic Investigations")
            score -= 10
        if not meds or meds.lower() in ["none", "nan", ""]:
            lapses.append("Missing Medication / Prescription Plan")
            score -= 10
        if not plan or plan.lower() in ["none", "nan", ""]:
            lapses.append("Missing Treatment Management Plan")
            score -= 10
        if not soap or soap.lower() in ["none", "nan", ""]:
            lapses.append("Missing Canonical SOAP Note Summary")
            score -= 10

        # 2. Diagnostic & ICD-10 Coding Consistency Check
        if diag and icd:
            expected_info = self.icd_mapper.lookup_diagnosis(diag)
            if expected_info and expected_info["code"].upper() != icd.upper():
                lapses.append(f"ICD-10 Mismatch: '{diag}' expected '{expected_info['code']}', but found '{icd}'")
                score -= 15
                severity = "Critical Lapse"

        # 3. Physiological Outlier & Vitals Anomaly Checks
        if exam:
            # HR check
            hr_match = re.search(r'HR\s*[:=\s]*(\d+)', exam, re.IGNORECASE)
            if hr_match:
                hr_val = int(hr_match.group(1))
                if hr_val < 30 or hr_val > 220:
                    lapses.append(f"Physiological Anomaly: Heart Rate ({hr_val} bpm) out of safe bounds (30-220)")
                    score -= 20
                    severity = "Critical Lapse"

            # Temp check
            temp_match = re.search(r'Temp\s*[:=\s]*([\d.]+)', exam, re.IGNORECASE)
            if temp_match:
                t_val = float(temp_match.group(1))
                if t_val < 34.0 or t_val > 42.5:
                    lapses.append(f"Physiological Anomaly: Temperature ({t_val} C) is biologically critical (<34C or >42.5C)")
                    score -= 20
                    severity = "Critical Lapse"

            # SpO2 check
            spo2_match = re.search(r'SpO2\s*[:=\s]*(\d+)', exam, re.IGNORECASE)
            if spo2_match:
                sp_val = int(spo2_match.group(1))
                if sp_val < 65:
                    lapses.append(f"Critical Hypoxia Alert: SpO2 ({sp_val}%) severely depressed (<65%)")
                    score -= 15
                    severity = "Critical Lapse"

        # 4. Medication Dosage Specificity Check
        if meds and meds.lower() not in ["none reported", "supportive care"]:
            if not re.search(r'\d+\s*(?:mg|g|mcg|ml|puffs?|tablets?|caps?)', meds, re.IGNORECASE):
                lapses.append("Medication Dosage Missing (Drug name listed without explicit dosage/frequency)")
                score -= 10

        # 5. Biometric Plausibility & Sex/Age Mismatch Checks
        plaus_anomalies = self.plausibility_validator.validate_record(row)
        for anom in plaus_anomalies:
            lapses.append(anom["description"])
            score -= 25
            if anom["severity"] == "Critical":
                severity = "Critical Lapse"

        score = max(0, min(100, score))

        if score < 60 or severity == "Critical Lapse":
            severity = "Critical Lapse"
        elif score < 90 or len(lapses) > 0:
            severity = "Minor Warning"
        else:
            severity = "Clean"

        return {
            "quality_score": score,
            "severity": severity,
            "lapse_count": len(lapses),
            "lapses": lapses,
            "lapse_summary": "; ".join(lapses) if lapses else "No lapses detected (100% Validated)"
        }

    def audit_dataframe(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Audits an entire DataFrame of clinical records and computes aggregate health metrics."""
        if df.empty:
            return {
                "total_records": 0,
                "clean_records": 0,
                "warning_records": 0,
                "critical_records": 0,
                "average_quality_score": 100.0,
                "audited_df": df
            }

        records = df.to_dict(orient="records")
        audited_results = [self.audit_record(r) for r in records]

        df_out = df.copy()
        df_out["Quality_Score"] = [res["quality_score"] for res in audited_results]
        df_out["Severity"] = [res["severity"] for res in audited_results]
        df_out["Lapse_Count"] = [res["lapse_count"] for res in audited_results]
        df_out["Lapses_Detected"] = [res["lapse_summary"] for res in audited_results]

        total = len(df_out)
        clean = int((df_out["Severity"] == "Clean").sum())
        warning = int((df_out["Severity"] == "Minor Warning").sum())
        critical = int((df_out["Severity"] == "Critical Lapse").sum())
        avg_score = round(float(df_out["Quality_Score"].mean()), 1)

        return {
            "total_records": total,
            "clean_records": clean,
            "warning_records": warning,
            "critical_records": critical,
            "average_quality_score": avg_score,
            "audited_df": df_out
        }

    def auto_rectify_record(self, row: Dict[str, Any]) -> Dict[str, Any]:
        """Applies automated AI structuring and ICD-10 rectification to fix identified lapses."""
        narrative = str(row.get("clinical_narrative") or "").strip()
        enc_id = str(row.get("source_encounter_id") or "E0001")
        var_id = int(row.get("variant_id") or 1)
        rec_id = str(row.get("id") or f"T2_{enc_id.replace('E', '')}_{str(var_id).zfill(2)}")

        # Enrich narrative with explicit row fields if present
        fragments = [narrative] if narrative else []
        if row.get("chief_complaint") and str(row["chief_complaint"]).lower() not in narrative.lower():
            fragments.append(f"Chief complaint: {row['chief_complaint']}.")
        if row.get("final_diagnosis") and str(row["final_diagnosis"]).lower() not in narrative.lower():
            fragments.append(f"Diagnosis: {row['final_diagnosis']}.")
        if row.get("exam") and str(row["exam"]).lower() not in narrative.lower():
            fragments.append(f"Exam: {row['exam']}.")
        if row.get("medications") and str(row["medications"]).lower() not in narrative.lower():
            fragments.append(f"Medications: {row['medications']}.")
        
        full_narrative = " ".join(fragments) if fragments else "Clinical consultation documented."

        # Re-extract with full clinical NLP and ontology mapping
        rectified = self.extractor.extract_record(
            clinical_narrative=full_narrative,
            encounter_id=enc_id,
            variant_id=var_id,
            record_id=rec_id
        )

        # Fallback check against explicit diagnosis provided in row
        if (not rectified.get("final_diagnosis") or rectified.get("icd10") == "R69") and row.get("final_diagnosis"):
            mapped = self.icd_mapper.lookup_diagnosis(str(row["final_diagnosis"]))
            if mapped:
                rectified["final_diagnosis"] = mapped["display"]
                rectified["icd10"] = mapped["code"]

        return rectified

    def auto_rectify_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """Rectifies all rows in a DataFrame to achieve 100% 15-column schema compliance."""
        records = df.to_dict(orient="records")
        rectified_records = [self.auto_rectify_record(r) for r in records]
        return pd.DataFrame(rectified_records)

    def sort_and_filter(
        self,
        df: pd.DataFrame,
        sort_by: str = "Quality_Score",
        ascending: bool = True,
        severity_filter: str = "All",
        search_query: str = "",
        min_quality_score: int = 0
    ) -> pd.DataFrame:
        """Sorts and filters audited clinical data with multi-column parameters."""
        filtered = df.copy()

        if severity_filter != "All" and "Severity" in filtered.columns:
            filtered = filtered[filtered["Severity"] == severity_filter]

        if min_quality_score > 0 and "Quality_Score" in filtered.columns:
            filtered = filtered[filtered["Quality_Score"] >= min_quality_score]

        if search_query:
            q = search_query.lower()
            str_cols = [c for c in filtered.columns if filtered[c].dtype == "object"]
            mask = filtered[str_cols].astype(str).apply(lambda col: col.str.lower().str.contains(q, na=False)).any(axis=1)
            filtered = filtered[mask]

        if sort_by in filtered.columns:
            filtered = filtered.sort_values(by=sort_by, ascending=ascending)

        return filtered
    def deidentify_dataset(self, df: pd.DataFrame) -> pd.DataFrame:
        """Strips all PHI / PII identifiers from the dataset (Safe Harbor & NDPA compliant)."""
        return self.deidentifier.deidentify_dataframe(df)
