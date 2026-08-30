import json
import os
from typing import Dict, Any, Optional
from fpdf import FPDF

def sanitize_pdf_text(text: Any) -> str:
    if text is None:
        return ""
    s = str(text)
    replacements = {
        "\u2022": "-",
        "\u2013": "-",
        "\u2014": "-",
        "\u2018": "'",
        "\u2019": "'",
        "\u201c": '"',
        "\u201d": '"',
        "\u2026": "..."
    }
    for k, v in replacements.items():
        s = s.replace(k, v)
    return s.encode('latin-1', 'replace').decode('latin-1')

class ClinicalDocumentExporter:
    """Exports clinical documentation into FHIR Bundle, Per-Patient PDF, JSON, and Markdown."""

    @staticmethod
    def to_json(data: Dict[str, Any], indent: int = 2) -> str:
        return json.dumps(data, indent=indent)

    @staticmethod
    def to_markdown(soap_data: Dict[str, Any]) -> str:
        meta = soap_data.get("metadata", {})
        patient_header = ""
        if meta:
            patient_header = (
                f"**Patient**: {meta.get('name', 'N/A')} | "
                f"**Age/Gender**: {meta.get('age', 'N/A')} {meta.get('gender', '')} | "
                f"**MRN**: {meta.get('mrn', 'N/A')}\n\n---\n\n"
            )

        return (
            f"# CLINICAL ENCOUNTER SUMMARY\n\n"
            f"{patient_header}"
            f"## [S] Subjective\n{soap_data.get('subjective', '')}\n\n"
            f"## [O] Objective\n{soap_data.get('objective', '')}\n\n"
            f"## [A] Assessment\n{soap_data.get('assessment', '')}\n\n"
            f"## [P] Plan\n{soap_data.get('plan', '')}\n"
        )

    @staticmethod
    def to_fhir_bundle(care_card: Dict[str, Any]) -> Dict[str, Any]:
        """Generates an HL7 FHIR R4 Bundle for interoperability."""
        enc_meta = care_card.get("encounter", {})
        i_inv = care_card.get("initial_investigation", {})
        u_rep = care_card.get("updated_report", {})
        enc_id = enc_meta.get("encounter_id", "E0001")
        p_name = enc_meta.get("patient_name", f"Patient {enc_id}")
        vitals = enc_meta.get("vitals", {})

        entries = [
            {
                "fullUrl": f"urn:uuid:Patient-{enc_id}",
                "resource": {
                    "resourceType": "Patient",
                    "id": f"pat-{enc_id}",
                    "name": [{"use": "official", "text": p_name}],
                    "gender": enc_meta.get("gender", "unknown").lower(),
                    "birthDate": "1990-01-01"
                }
            },
            {
                "fullUrl": f"urn:uuid:Encounter-{enc_id}",
                "resource": {
                    "resourceType": "Encounter",
                    "id": f"enc-{enc_id}",
                    "status": "finished" if "Completed" in enc_meta.get("status", "") else "in-progress",
                    "class": {"system": "http://terminology.hl7.org/CodeSystem/v3-ActCode", "code": "AMB", "display": "Ambulatory"},
                    "subject": {"reference": f"Patient/pat-{enc_id}", "display": p_name},
                    "participant": [
                        {"individual": {"display": enc_meta.get("assigned_doctor", "Attending Doctor")}}
                    ]
                }
            }
        ]

        # Observation (Vitals with LOINC codes)
        loinc_map = {
            "BP": {"code": "85354-9", "display": "Blood pressure panel with all children optional"},
            "HR": {"code": "8867-4", "display": "Heart rate"},
            "Temp": {"code": "8310-5", "display": "Body temperature"},
            "RR": {"code": "9279-1", "display": "Respiratory rate"},
            "SpO2": {"code": "2708-6", "display": "Oxygen saturation in Arterial blood"}
        }

        for v_key, v_val in vitals.items():
            l_info = loinc_map.get(v_key, {"code": "vital-custom", "display": v_key})
            entries.append({
                "fullUrl": f"urn:uuid:Observation-{enc_id}-{v_key}",
                "resource": {
                    "resourceType": "Observation",
                    "status": "final",
                    "code": {
                        "coding": [{"system": "http://loinc.org", "code": l_info["code"], "display": l_info["display"]}],
                        "text": v_key
                    },
                    "subject": {"reference": f"Patient/pat-{enc_id}"},
                    "valueString": str(v_val)
                }
            })

        # Condition (ICD-10 & SNOMED CT)
        u_diag = u_rep.get("final_diagnosis") if u_rep else None
        i_diag = i_inv.get("final_diagnosis") if i_inv else None
        primary_diag = u_diag or i_diag or "Unspecified Condition"
        u_icd = u_rep.get("icd10") if u_rep else None
        i_icd = i_inv.get("icd10") if i_inv else None
        icd_code = u_icd or i_icd or "R69"

        entries.append({
            "fullUrl": f"urn:uuid:Condition-{enc_id}",
            "resource": {
                "resourceType": "Condition",
                "clinicalStatus": {"coding": [{"system": "http://terminology.hl7.org/CodeSystem/condition-clinical", "code": "active"}]},
                "code": {
                    "coding": [
                        {"system": "http://hl7.org/fhir/sid/icd-10", "code": icd_code, "display": primary_diag},
                        {"system": "http://snomed.info/sct", "code": "404684003", "display": primary_diag}
                    ],
                    "text": primary_diag
                },
                "subject": {"reference": f"Patient/pat-{enc_id}"}
            }
        })

        # DiagnosticReport (Lab results)
        if u_rep:
            entries.append({
                "fullUrl": f"urn:uuid:DiagnosticReport-{enc_id}",
                "resource": {
                    "resourceType": "DiagnosticReport",
                    "status": "final",
                    "code": {"text": "Laboratory Findings & Confirmation"},
                    "subject": {"reference": f"Patient/pat-{enc_id}"},
                    "conclusion": u_rep.get("investigations", "Lab results finalized"),
                    "performer": [{"display": u_rep.get("author_name", "Lab Technician")}]
                }
            })

        return {
            "resourceType": "Bundle",
            "type": "document",
            "timestamp": "2026-08-30T10:00:00Z",
            "total": len(entries),
            "entry": entries
        }

    @staticmethod
    def generate_patient_pdf(care_card: Dict[str, Any], output_path: str) -> str:
        """Generates a clean, institutional per-patient PDF care report."""
        enc = care_card.get("encounter", {})
        i_inv = care_card.get("initial_investigation", {})
        u_rep = care_card.get("updated_report", {})
        enc_id = enc.get("encounter_id", "E0001")
        p_name = enc.get("patient_name", f"Patient {enc_id}")

        pdf = FPDF()
        pdf.set_auto_page_break(auto=True, margin=15)
        pdf.add_page()

        # Header Block
        pdf.set_fill_color(30, 58, 138)
        pdf.rect(0, 0, 210, 28, 'F')
        pdf.set_font("Helvetica", "B", 14)
        pdf.set_text_color(255, 255, 255)
        pdf.set_y(6)
        pdf.cell(0, 6, "MediScribe AI - Reconciled Patient Care Card", 0, 1, "C")
        pdf.set_font("Helvetica", "", 8.5)
        pdf.set_text_color(224, 231, 255)
        pdf.cell(0, 5, f"Official Clinical Encounter Summary | Encounter ID: {enc_id}", 0, 1, "C")

        pdf.set_y(34)
        pdf.set_text_color(30, 41, 59)

        # Patient Info Grid
        pdf.set_font("Helvetica", "B", 9)
        pdf.cell(30, 5, "Patient Name:", 0, 0)
        pdf.set_font("Helvetica", "", 9)
        pdf.cell(60, 5, sanitize_pdf_text(p_name), 0, 0)
        pdf.set_font("Helvetica", "B", 9)
        pdf.cell(30, 5, "Age / Gender:", 0, 0)
        pdf.set_font("Helvetica", "", 9)
        pdf.cell(0, 5, f"{str(enc.get('age') or 45)} yrs / {str(enc.get('gender') or 'Female')}", 0, 1)

        pdf.set_font("Helvetica", "B", 9)
        pdf.cell(30, 5, "Status:", 0, 0)
        pdf.set_font("Helvetica", "", 9)
        pdf.cell(60, 5, str(enc.get("status") or "Active"), 0, 0)
        pdf.set_font("Helvetica", "B", 9)
        pdf.cell(30, 5, "Attending MD:", 0, 0)
        pdf.set_font("Helvetica", "", 9)
        pdf.cell(0, 5, sanitize_pdf_text(str(enc.get("assigned_doctor") or "Dr. Sarah Smith, MD")), 0, 1)

        pdf.ln(2)
        pdf.set_draw_color(203, 213, 225)
        pdf.line(10, pdf.get_y(), 200, pdf.get_y())
        pdf.ln(3)

        # Baseline Vitals
        pdf.set_font("Helvetica", "B", 9.5)
        pdf.set_text_color(30, 58, 138)
        pdf.cell(0, 5.5, "1. Triage Nurse Intake & Baseline Vitals", 0, 1)
        pdf.set_font("Helvetica", "", 8.5)
        pdf.set_text_color(30, 41, 59)
        v_str = ", ".join([f"{k}: {v}" for k, v in enc.get("vitals", {}).items()]) if enc.get("vitals") else "Vitals recorded in EHR"
        pdf.cell(0, 4.5, sanitize_pdf_text(f"Vitals Recorded: {v_str}"), 0, 1)
        pdf.cell(0, 4.5, sanitize_pdf_text(f"Chief Complaint: {enc.get('chief_complaint', 'Medical consultation')}"), 0, 1)
        pdf.ln(2)

        # Pre-Lab Doctor Note
        pdf.set_font("Helvetica", "B", 9.5)
        pdf.set_text_color(30, 58, 138)
        pdf.cell(0, 5.5, "2. Attending Physician Initial Examination (Pre-Lab)", 0, 1)
        pdf.set_font("Helvetica", "", 8.5)
        pdf.set_text_color(30, 41, 59)
        if i_inv:
            pdf.multi_cell(0, 4.2, sanitize_pdf_text(f"Preliminary Diagnosis: {i_inv.get('final_diagnosis')} (ICD-10: {i_inv.get('icd10')}) | Ordered Tests: {i_inv.get('investigations')}\nHPI: {i_inv.get('hpi')}\nPhysical Exam: {i_inv.get('exam')}"))
        else:
            pdf.cell(0, 4.5, "Initial physician assessment recorded.", 0, 1)
        pdf.ln(2)

        # Post-Lab Report
        pdf.set_font("Helvetica", "B", 9.5)
        pdf.set_text_color(30, 58, 138)
        pdf.cell(0, 5.5, "3. Laboratory Diagnostic Results & Confirmation (Post-Lab)", 0, 1)
        pdf.set_font("Helvetica", "", 8.5)
        pdf.set_text_color(30, 41, 59)
        if u_rep:
            pdf.multi_cell(0, 4.2, sanitize_pdf_text(f"Confirmed Diagnosis: {u_rep.get('final_diagnosis')} (ICD-10: {u_rep.get('icd10')})\nLab Findings & Values: {u_rep.get('investigations')}\nTechnician Attribution: {u_rep.get('author_name')}"))
        else:
            pdf.cell(0, 4.5, "Laboratory results pending.", 0, 1)
        pdf.ln(2)

        # Comprehensive Final SOAP Note
        pdf.set_font("Helvetica", "B", 9.5)
        pdf.set_text_color(30, 58, 138)
        pdf.cell(0, 5.5, "4. Finalized Comprehensive SOAP Note & Regimen", 0, 1)
        pdf.set_font("Helvetica", "", 8)
        pdf.set_text_color(30, 41, 59)
        soap_content = (u_rep.get("soap_note") if u_rep else i_inv.get("soap_note")) or "SOAP summary finalized."
        pdf.set_fill_color(248, 250, 252)
        pdf.multi_cell(0, 4, sanitize_pdf_text(soap_content), border=1, fill=True)

        pdf.output(output_path)
        return output_path