import sqlite3
import os
import pandas as pd
from datetime import datetime
from typing import Dict, Any, List, Optional
from src.nlp.organizer_extractor import OrganizerRecordExtractor

DB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../data/registry/central_clinical_registry.db'))

class CentralClinicalRegistry:
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self.extractor = OrganizerRecordExtractor()
        self.init_db()

    def get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def init_db(self):
        conn = self.get_connection()
        try:
            cursor = conn.cursor()

            cursor.execute('''
                CREATE TABLE IF NOT EXISTS patient_encounters (
                    encounter_id TEXT PRIMARY KEY,
                    patient_name TEXT NOT NULL,
                    patient_age INTEGER,
                    patient_gender TEXT,
                    assigned_doctor TEXT,
                    status TEXT DEFAULT 'Nurse Intake',
                    nurse_vitals TEXT,
                    doctor_initial_notes TEXT,
                    lab_results TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            cursor.execute('''
                CREATE TABLE IF NOT EXISTS raw_variants (
                    id TEXT PRIMARY KEY,
                    source_encounter_id TEXT NOT NULL,
                    variant_id INTEGER NOT NULL,
                    author_role TEXT DEFAULT 'Technician',
                    author_name TEXT DEFAULT 'Staff',
                    stage TEXT DEFAULT 'Clinical Review',
                    clinical_narrative TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            cursor.execute('''
                CREATE TABLE IF NOT EXISTS structured_records (
                    id TEXT PRIMARY KEY,
                    source_encounter_id TEXT NOT NULL,
                    variant_id INTEGER NOT NULL,
                    author_name TEXT DEFAULT 'Staff',
                    author_role TEXT DEFAULT 'Technician',
                    clinical_narrative TEXT NOT NULL,
                    chief_complaint TEXT,
                    hpi TEXT,
                    pmh TEXT,
                    exam TEXT,
                    differential TEXT,
                    final_diagnosis TEXT,
                    icd10 TEXT,
                    investigations TEXT,
                    medications TEXT,
                    treatment_plan TEXT,
                    soap_note TEXT,
                    report_type TEXT DEFAULT 'Initial Investigation',
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (id) REFERENCES raw_variants (id)
                )
            ''')

            cursor.execute('''
                CREATE TABLE IF NOT EXISTS audit_logs (
                    log_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    record_id TEXT NOT NULL,
                    action TEXT NOT NULL,
                    editor_name TEXT NOT NULL,
                    details TEXT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            conn.commit()
        finally:
            conn.close()

    def submit_report(
        self,
        clinical_narrative: str,
        source_encounter_id: str = "E0001",
        author_role: str = "Technician",
        author_name: str = "Staff"
    ) -> Dict[str, Any]:
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT MAX(variant_id) FROM raw_variants WHERE source_encounter_id = ?", (source_encounter_id,))
            max_v = cursor.fetchone()[0]
            next_variant = 1 if max_v is None else max_v + 1
            record_id = f"T2_{source_encounter_id.replace('E', '')}_V{str(next_variant).zfill(2)}"

            cursor.execute('''
                INSERT OR REPLACE INTO raw_variants (id, source_encounter_id, variant_id, author_role, author_name, clinical_narrative)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (record_id, source_encounter_id, next_variant, author_role, author_name, clinical_narrative))

            structured = self.extractor.extract_record(
                clinical_narrative=clinical_narrative,
                encounter_id=source_encounter_id,
                variant_id=next_variant,
                record_id=record_id
            )

            cursor.execute('''
                INSERT OR REPLACE INTO structured_records (
                    id, source_encounter_id, variant_id, author_name, author_role, clinical_narrative,
                    chief_complaint, hpi, pmh, exam, differential,
                    final_diagnosis, icd10, investigations, medications,
                    treatment_plan, soap_note, report_type
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'Initial Investigation')
            ''', (
                structured["id"], structured["source_encounter_id"], structured["variant_id"],
                author_name, author_role,
                structured["clinical_narrative"], structured["chief_complaint"], structured["hpi"],
                structured["pmh"], structured["exam"], structured["differential"],
                structured["final_diagnosis"], structured["icd10"], structured["investigations"],
                structured["medications"], structured["treatment_plan"], structured["soap_note"]
            ))

            conn.commit()
            return structured
        finally:
            conn.close()

    def nurse_intake(
        self,
        encounter_id: str,
        patient_name: str,
        patient_age: int,
        patient_gender: str,
        vitals_dict: Dict[str, str],
        chief_complaint: str,
        assigned_doctor: str,
        nurse_name: str = "Nurse Amina"
    ) -> Dict[str, Any]:
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            vitals_str = ", ".join([f"{k}: {v}" for k, v in vitals_dict.items() if v])
            narrative = f"Patient: {patient_name}, {patient_age} yo {patient_gender}. CC: {chief_complaint}. Vitals: {vitals_str}."

            cursor.execute('''
                INSERT OR REPLACE INTO patient_encounters (
                    encounter_id, patient_name, patient_age, patient_gender,
                    assigned_doctor, status, nurse_vitals, updated_at
                ) VALUES (?, ?, ?, ?, ?, 'Doctor Queue', ?, CURRENT_TIMESTAMP)
            ''', (encounter_id, patient_name, patient_age, patient_gender, assigned_doctor, vitals_str))

            rec_id = f"T2_{encounter_id.replace('E', '')}_V01"
            cursor.execute('''
                INSERT OR REPLACE INTO raw_variants (id, source_encounter_id, variant_id, author_role, author_name, stage, clinical_narrative)
                VALUES (?, ?, 1, 'Triage Nurse', ?, 'Nurse Intake', ?)
            ''', (rec_id, encounter_id, nurse_name, narrative))

            structured = self.extractor.extract_record(narrative, encounter_id=encounter_id, variant_id=1, record_id=rec_id)
            cursor.execute('''
                INSERT OR REPLACE INTO structured_records (
                    id, source_encounter_id, variant_id, author_name, author_role, clinical_narrative,
                    chief_complaint, hpi, pmh, exam, differential,
                    final_diagnosis, icd10, investigations, medications,
                    treatment_plan, soap_note, report_type
                ) VALUES (?, ?, ?, ?, 'Triage Nurse', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'Nurse Intake')
            ''', (
                rec_id, encounter_id, 1, nurse_name, narrative,
                chief_complaint, structured["hpi"], structured["pmh"], vitals_str,
                structured["differential"], structured["final_diagnosis"], structured["icd10"],
                structured["investigations"], structured["medications"], structured["treatment_plan"], structured["soap_note"]
            ))

            cursor.execute('''
                INSERT INTO audit_logs (record_id, action, editor_name, details)
                VALUES (?, 'NURSE_INTAKE', ?, ?)
            ''', (encounter_id, nurse_name, f"Assigned to {assigned_doctor} with vitals: {vitals_str}"))

            conn.commit()
            return {"encounter_id": encounter_id, "status": "Doctor Queue", "assigned_doctor": assigned_doctor}
        finally:
            conn.close()

    def doctor_submit_investigation(
        self,
        encounter_id: str,
        structured_data: Dict[str, Any],
        send_to_lab: bool = True,
        doctor_name: str = "Dr. Sarah Smith, MD"
    ) -> Dict[str, Any]:
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            status = "Lab Queue" if send_to_lab else "Completed"
            
            cursor.execute("SELECT MAX(variant_id) FROM raw_variants WHERE source_encounter_id = ?", (encounter_id,))
            max_v = cursor.fetchone()[0]
            next_variant = 2 if max_v is None else max_v + 1
            record_id = f"T2_{encounter_id.replace('E', '')}_V{str(next_variant).zfill(2)}"

            cursor.execute('''
                UPDATE patient_encounters SET
                    status = ?,
                    doctor_initial_notes = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE encounter_id = ?
            ''', (status, structured_data.get("soap_note", ""), encounter_id))

            cursor.execute('''
                INSERT INTO raw_variants (id, source_encounter_id, variant_id, author_role, author_name, stage, clinical_narrative)
                VALUES (?, ?, ?, 'Attending Physician', ?, 'Doctor Review', ?)
            ''', (record_id, encounter_id, next_variant, doctor_name, structured_data.get("clinical_narrative", "")))

            cursor.execute('''
                INSERT INTO structured_records (
                    id, source_encounter_id, variant_id, author_name, author_role, clinical_narrative,
                    chief_complaint, hpi, pmh, exam, differential,
                    final_diagnosis, icd10, investigations, medications,
                    treatment_plan, soap_note, report_type
                ) VALUES (?, ?, ?, ?, 'Attending Physician', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'Initial Investigation')
            ''', (
                record_id, encounter_id, next_variant, doctor_name,
                structured_data.get("clinical_narrative", ""),
                structured_data.get("chief_complaint", ""),
                structured_data.get("hpi", ""),
                structured_data.get("pmh", ""),
                structured_data.get("exam", ""),
                structured_data.get("differential", ""),
                structured_data.get("final_diagnosis", ""),
                structured_data.get("icd10", ""),
                structured_data.get("investigations", ""),
                structured_data.get("medications", ""),
                structured_data.get("treatment_plan", ""),
                structured_data.get("soap_note", "")
            ))

            cursor.execute('''
                INSERT INTO audit_logs (record_id, action, editor_name, details)
                VALUES (?, 'DOCTOR_REVIEW', ?, ?)
            ''', (record_id, doctor_name, f"Doctor structured note saved. Status: {status}"))

            conn.commit()
            return {"record_id": record_id, "status": status}
        finally:
            conn.close()

    def lab_submit_results(
        self,
        encounter_id: str,
        lab_results_text: str,
        confirmed_diagnosis: str,
        confirmed_icd10: str,
        lab_tech_name: str = "Onahi Emmanuel, Tech"
    ) -> Dict[str, Any]:
        conn = self.get_connection()
        try:
            cursor = conn.cursor()

            cursor.execute("SELECT MAX(variant_id) FROM raw_variants WHERE source_encounter_id = ?", (encounter_id,))
            max_v = cursor.fetchone()[0]
            next_variant = 3 if max_v is None else max_v + 1
            record_id = f"T2_{encounter_id.replace('E', '')}_V{str(next_variant).zfill(2)}"

            cursor.execute('''
                UPDATE patient_encounters SET
                    status = 'Completed',
                    lab_results = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE encounter_id = ?
            ''', (lab_results_text, encounter_id))

            cursor.execute('''
                SELECT * FROM structured_records 
                WHERE source_encounter_id = ? AND report_type = 'Initial Investigation'
                ORDER BY variant_id DESC LIMIT 1
            ''', (encounter_id,))
            doc_note = cursor.fetchone()

            cc = doc_note["chief_complaint"] if doc_note else "Clinical Evaluation"
            exam = doc_note["exam"] if doc_note else "Vitals stable"
            meds = doc_note["medications"] if doc_note else "Standard therapy"
            hpi = doc_note["hpi"] if doc_note else ""
            pmh = doc_note["pmh"] if doc_note else ""

            post_lab_narrative = f"Lab Results: {lab_results_text}. Confirmed Diagnosis: {confirmed_diagnosis} (ICD-10: {confirmed_icd10})."
            updated_soap = f"S: {cc}. O: Exam: {exam}; Lab Results: {lab_results_text}. A: Confirmed {confirmed_diagnosis} (ICD-10: {confirmed_icd10}). P: {meds}."

            cursor.execute('''
                INSERT INTO raw_variants (id, source_encounter_id, variant_id, author_role, author_name, stage, clinical_narrative)
                VALUES (?, ?, ?, 'Technician', ?, 'Lab Results', ?)
            ''', (record_id, encounter_id, next_variant, lab_tech_name, post_lab_narrative))

            cursor.execute('''
                INSERT INTO structured_records (
                    id, source_encounter_id, variant_id, author_name, author_role, clinical_narrative,
                    chief_complaint, hpi, pmh, exam, differential,
                    final_diagnosis, icd10, investigations, medications,
                    treatment_plan, soap_note, report_type
                ) VALUES (?, ?, ?, ?, 'Technician', ?, ?, ?, ?, ?, 'Confirmed by laboratory evaluation', ?, ?, ?, ?, ?, ?, 'Updated Report')
            ''', (
                record_id, encounter_id, next_variant, lab_tech_name,
                post_lab_narrative, cc, hpi, pmh, f"{exam}; Lab: {lab_results_text}",
                confirmed_diagnosis, confirmed_icd10, lab_results_text, meds,
                f"Definitive treatment for {confirmed_diagnosis}", updated_soap
            ))

            cursor.execute('''
                INSERT INTO audit_logs (record_id, action, editor_name, details)
                VALUES (?, 'LAB_RESULTS', ?, ?)
            ''', (record_id, lab_tech_name, f"Lab results filed: {lab_results_text}"))

            conn.commit()
            return {"record_id": record_id, "status": "Completed"}
        finally:
            conn.close()

    def get_care_card(self, encounter_id: str) -> Dict[str, Any]:
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM patient_encounters WHERE encounter_id = ?", (encounter_id,))
            encounter = cursor.fetchone()
            if not encounter:
                return {}

            cursor.execute('''
                SELECT * FROM structured_records 
                WHERE source_encounter_id = ? 
                ORDER BY variant_id ASC
            ''', (encounter_id,))
            records = [dict(r) for r in cursor.fetchall()]

            initial_inv = next((r for r in records if r.get("report_type") == "Initial Investigation"), None)
            if not initial_inv and records:
                initial_inv = records[0]

            updated_rep = next((r for r in records if r.get("report_type") == "Updated Report"), None)
            if not updated_rep and len(records) > 1:
                updated_rep = records[-1]

            return {
                "encounter": dict(encounter),
                "initial_investigation": initial_inv,
                "updated_report": updated_rep,
                "all_variants": records
            }
        finally:
            conn.close()

    def get_all_records_df(self) -> pd.DataFrame:
        conn = self.get_connection()
        try:
            df = pd.read_sql_query('''
                SELECT id, source_encounter_id, variant_id, author_name, author_role,
                       report_type, clinical_narrative, chief_complaint, hpi, pmh, exam, differential,
                       final_diagnosis, icd10, investigations, medications,
                       treatment_plan, soap_note, updated_at
                FROM structured_records
                ORDER BY source_encounter_id, variant_id
            ''', conn)
            return df
        finally:
            conn.close()

    def search_and_filter(
        self,
        search_query: str = "",
        encounter_id: str = "All",
        diagnosis: str = "All",
        icd10: str = "All",
        role: str = "All"
    ) -> pd.DataFrame:
        df = self.get_all_records_df()
        if df.empty:
            return df

        if encounter_id not in ["All", "All Encounters"] and "source_encounter_id" in df.columns:
            df = df[df["source_encounter_id"] == encounter_id]

        if diagnosis not in ["All", "All Diagnoses"] and "final_diagnosis" in df.columns:
            df = df[df["final_diagnosis"] == diagnosis]

        if icd10 not in ["All", "All ICD-10 Codes"] and "icd10" in df.columns:
            df = df[df["icd10"] == icd10]

        role_col = "author_role" if "author_role" in df.columns else None
        if role_col and role not in ["All", "All Roles"]:
            df = df[df[role_col] == role]

        if search_query.strip():
            q = search_query.strip().lower()
            df = df[
                df["clinical_narrative"].astype(str).str.lower().str.contains(q) |
                df["chief_complaint"].astype(str).str.lower().str.contains(q) |
                df["final_diagnosis"].astype(str).str.lower().str.contains(q) |
                df["medications"].astype(str).str.lower().str.contains(q) |
                df["soap_note"].astype(str).str.lower().str.contains(q) |
                df["id"].astype(str).str.lower().str.contains(q) |
                df["author_name"].astype(str).str.lower().str.contains(q)
            ]

        return df

    def get_encounters_by_doctor(self, doctor_name: str) -> List[Dict[str, Any]]:
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM patient_encounters WHERE assigned_doctor = ? OR assigned_doctor LIKE ?", 
                           (doctor_name, f"%{doctor_name.split()[0]}%"))
            return [dict(r) for r in cursor.fetchall()]
        finally:
            conn.close()

    def get_pending_lab_encounters(self) -> List[Dict[str, Any]]:
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM patient_encounters WHERE status = 'Lab Queue' OR status = 'Pending Lab'")
            return [dict(r) for r in cursor.fetchall()]
        finally:
            conn.close()

    def update_record(self, record_id: str, updates: Dict[str, Any], editor_name: str = "Staff") -> bool:
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            set_clauses = []
            values = []
            
            allowed_cols = [
                'chief_complaint', 'hpi', 'pmh', 'exam', 'differential',
                'final_diagnosis', 'icd10', 'investigations', 'medications',
                'treatment_plan', 'soap_note'
            ]

            for k, v in updates.items():
                if k in allowed_cols:
                    set_clauses.append(f"{k} = ?")
                    values.append(v)

            if not set_clauses:
                return False

            set_clauses.append("updated_at = CURRENT_TIMESTAMP")
            values.append(record_id)

            sql = f"UPDATE structured_records SET {', '.join(set_clauses)} WHERE id = ?"
            cursor.execute(sql, values)

            cursor.execute('''
                INSERT INTO audit_logs (record_id, action, editor_name, details)
                VALUES (?, 'UPDATE', ?, ?)
            ''', (record_id, editor_name, f"Updated fields: {', '.join(updates.keys())}"))

            conn.commit()
            return True
        finally:
            conn.close()

    def delete_record(self, record_id: str, editor_name: str = "Staff") -> bool:
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM structured_records WHERE id = ?", (record_id,))
            cursor.execute('''
                INSERT INTO audit_logs (record_id, action, editor_name, details)
                VALUES (?, 'DELETE', ?, 'Record removed from active registry')
            ''', (record_id, editor_name))
            conn.commit()
            return True
        finally:
            conn.close()

    def bulk_import_dataframe(self, df: pd.DataFrame, author_name: str = "Staff", author_role: str = "Technician") -> int:
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            inserted = 0

            cols_lower = {str(c).lower().strip(): c for c in df.columns}

            for idx, row in df.iterrows():
                enc_id = "E" + str(idx + 1).zfill(4)
                for possible in ['source_encounter_id', 'encounter_id', 'encounter', 'patient_id']:
                    if possible in cols_lower:
                        enc_id = str(row[cols_lower[possible]])
                        break

                narrative = ""
                for possible in ['clinical_narrative', 'narrative', 'report', 'text', 'notes', 'dialogue']:
                    if possible in cols_lower:
                        narrative = str(row[cols_lower[possible]])
                        break

                if not narrative or narrative == "nan":
                    narrative = " ".join([f"{k}: {v}" for k, v in row.items() if pd.notna(v)])

                var_id = 1
                if 'variant_id' in cols_lower:
                    try:
                        var_id = int(row[cols_lower['variant_id']])
                    except:
                        var_id = 1

                rec_id = f"T2_{enc_id.replace('E', '')}_V{str(var_id).zfill(2)}"
                if df.columns[0] in ['id', '6665'] and pd.notna(row[df.columns[0]]):
                    rec_id = str(row[df.columns[0]])

                if 'chief_complaint' in cols_lower and pd.notna(row.get(cols_lower['chief_complaint'])):
                    cc = str(row.get(cols_lower['chief_complaint'], ''))
                    hpi = str(row.get(cols_lower.get('hpi', ''), ''))
                    pmh = str(row.get(cols_lower.get('pmh', ''), ''))
                    exam = str(row.get(cols_lower.get('exam', ''), ''))
                    diff = str(row.get(cols_lower.get('differential', ''), ''))
                    diag = str(row.get(cols_lower.get('final_diagnosis', ''), ''))
                    icd = str(row.get(cols_lower.get('icd10', ''), ''))
                    inv = str(row.get(cols_lower.get('investigations', ''), ''))
                    meds = str(row.get(cols_lower.get('medications', ''), ''))
                    plan = str(row.get(cols_lower.get('treatment_plan', ''), ''))
                    soap = str(row.get(cols_lower.get('soap_note', ''), ''))
                else:
                    structured = self.extractor.extract_record(narrative, encounter_id=enc_id, variant_id=var_id, record_id=rec_id)
                    cc = structured["chief_complaint"]
                    hpi = structured["hpi"]
                    pmh = structured["pmh"]
                    exam = structured["exam"]
                    diff = structured["differential"]
                    diag = structured["final_diagnosis"]
                    icd = structured["icd10"]
                    inv = structured["investigations"]
                    meds = structured["medications"]
                    plan = structured["treatment_plan"]
                    soap = structured["soap_note"]

                cursor.execute('''
                    INSERT OR REPLACE INTO patient_encounters (encounter_id, patient_name, status)
                    VALUES (?, ?, 'Completed')
                ''', (enc_id, f"Patient {enc_id}"))

                cursor.execute('''
                    INSERT OR REPLACE INTO raw_variants (id, source_encounter_id, variant_id, author_name, author_role, clinical_narrative)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (rec_id, enc_id, var_id, author_name, author_role, narrative))

                cursor.execute('''
                    INSERT OR REPLACE INTO structured_records (
                        id, source_encounter_id, variant_id, author_name, author_role, clinical_narrative,
                        chief_complaint, hpi, pmh, exam, differential,
                        final_diagnosis, icd10, investigations, medications,
                        treatment_plan, soap_note, report_type
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'Initial Investigation')
                ''', (
                    rec_id, enc_id, var_id, author_name, author_role, narrative,
                    cc, hpi, pmh, exam, diff, diag, icd, inv, meds, plan, soap
                ))
                inserted += 1

            cursor.execute('''
                INSERT INTO audit_logs (record_id, action, editor_name, details)
                VALUES ('BULK', 'BULK_IMPORT', ?, ?)
            ''', (author_name, f"Bulk imported {inserted} records"))

            conn.commit()
            return inserted
        finally:
            conn.close()


    def export_to_csv(self, output_path: str) -> str:
        df = self.get_all_records_df()
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        df.to_csv(output_path, index=False)
        return output_path

    def get_audit_logs_df(self) -> pd.DataFrame:
        conn = self.get_connection()
        try:
            return pd.read_sql_query("SELECT * FROM audit_logs ORDER BY timestamp DESC LIMIT 100", conn)
        finally:
            conn.close()
