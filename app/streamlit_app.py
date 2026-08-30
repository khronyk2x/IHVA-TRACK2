import streamlit as st
import pandas as pd
import json
import sys
import os
from io import BytesIO

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.auth.auth_manager import AuthManager
from src.preprocessing.cleaner import ClinicalTextCleaner
from src.preprocessing.segmenter import ClinicalSectionSegmenter
from src.nlp.entity_extractor import ClinicalEntityExtractor
from src.nlp.soap_generator import ClinicalSOAPGenerator
from src.models.classifier import ClinicalNoteClassifier
from src.models.llm_engine import ClinicalLLMEngine
from src.nlp.icd10_mapper import ICD10OntologyMapper
from src.nlp.organizer_extractor import OrganizerRecordExtractor
from src.database.registry import CentralClinicalRegistry
from src.ocr.image_scanner import ClinicalOCRScanner
from src.audio.transcriber import MultilingualClinicalAudioTranscriber
from src.utils.sample_cases import SAMPLE_CASES
from src.utils.exporter import ClinicalDocumentExporter

st.set_page_config(
    page_title="MediScribe AI - Clinical Care Card & Central Registry",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown('''
<style>
    .main .block-container { padding-top: 1.2rem; padding-bottom: 5rem; max-width: 100%; }
    .main-header { font-size: 1.8rem; font-weight: 700; color: #1E3A8A; margin-bottom: 0.2rem; }
    .sub-header { font-size: 0.92rem; color: #4B5563; margin-bottom: 0.8rem; }
    .card-box { background-color: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 8px; padding: 14px; margin-bottom: 12px; }
    .user-badge { display: inline-block; background-color: #EFF6FF; border: 1px solid #BFDBFE; color: #1E40AF; padding: 4px 10px; border-radius: 6px; font-size: 0.85rem; font-weight: 600; margin-bottom: 8px; }
    .stage-badge { display: inline-block; padding: 3px 8px; border-radius: 4px; font-size: 0.8rem; font-weight: 600; margin-right: 6px; }
    .stage-intake { background: #FEF3C7; color: #92400E; }
    .stage-doctor { background: #DBEAFE; color: #1E40AF; }
    .stage-lab { background: #FCE7F3; color: #9D174D; }
    .stage-completed { background: #D1FAE5; color: #065F46; }
    @media (max-width: 768px) {
        .main-header { font-size: 1.35rem; }
        .sub-header { font-size: 0.82rem; }
        .stButton>button { width: 100%; margin-bottom: 6px; }
    }
    .mobile-bottom-nav { display: none; }
    @media (max-width: 768px) {
        .mobile-bottom-nav {
            display: flex; position: fixed; bottom: 0; left: 0; right: 0;
            background: #1E3A8A; color: white; justify-content: space-around;
            padding: 10px 0; z-index: 999999; box-shadow: 0 -2px 10px rgba(0,0,0,0.15);
            font-size: 0.75rem; font-weight: 600; text-align: center;
        }
    }
</style>
''', unsafe_allow_html=True)

@st.cache_resource
def load_nlp_components():
    cleaner = ClinicalTextCleaner(expand_abbreviations=True)
    extractor = ClinicalEntityExtractor()
    generator = ClinicalSOAPGenerator()
    classifier = ClinicalNoteClassifier()
    classifier.train_baseline()
    llm_engine = ClinicalLLMEngine()
    icd_mapper = ICD10OntologyMapper()
    org_extractor = OrganizerRecordExtractor()
    ocr_scanner = ClinicalOCRScanner()
    audio_transcriber = MultilingualClinicalAudioTranscriber()
    return cleaner, extractor, generator, classifier, llm_engine, icd_mapper, org_extractor, ocr_scanner, audio_transcriber

cleaner, extractor, generator, classifier, llm_engine, icd_mapper, org_extractor, ocr_scanner, audio_transcriber = load_nlp_components()

registry = CentralClinicalRegistry()

if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False
if "current_user" not in st.session_state:
    st.session_state["current_user"] = None
if "transcript_text" not in st.session_state:
    st.session_state["transcript_text"] = SAMPLE_CASES["Case 1: Cardiology Consult (Chest Pain & HTN)"]["text"]
if "selected_case" not in st.session_state:
    st.session_state["selected_case"] = "Case 1: Cardiology Consult (Chest Pain & HTN)"
if "doc_structured_edit" not in st.session_state:
    st.session_state["doc_structured_edit"] = None
if "show_ocr_drawer" not in st.session_state:
    st.session_state["show_ocr_drawer"] = False
if "show_audio_drawer" not in st.session_state:
    st.session_state["show_audio_drawer"] = False
if "chat_history" not in st.session_state:
    st.session_state["chat_history"] = [
        {"role": "assistant", "content": "Hello. I am the Clinical Guidance & Case Recall Assistant. You can ask me medical questions, check WHO IDSR definitions, or query past patient records from the Central Database."}
    ]

if not st.session_state["authenticated"]:
    st.markdown('<div class="main-header">MediScribe AI - Secure Clinical Login</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Role-based access: Nurse Intake -> Doctor Queue -> Lab Results -> Patient Care Card.</div>', unsafe_allow_html=True)

    col_l1, col_l2, col_l3 = st.columns([1, 1.2, 1])
    with col_l2:
        with st.form("login_form"):
            st.subheader("Sign In")
            login_username = st.text_input("Username / Staff ID:")
            login_password = st.text_input("Password:", type="password")
            login_submit = st.form_submit_button("Sign In", type="primary", use_container_width=True)

            if login_submit:
                user_info = AuthManager.authenticate(login_username, login_password)
                if user_info:
                    st.session_state["authenticated"] = True
                    st.session_state["current_user"] = user_info
                    st.success(f"Welcome, {user_info['name']} ({user_info['role']})")
                    st.rerun()
                else:
                    st.error("Invalid credentials. Please enter valid staff credentials.")

        st.markdown("---")
        st.info('''
        - **Physician**: `dr_smith` / `doctor123` (Attending Physician - reviews assigned patients)
        - **Triage Nurse**: `nurse_amina` / `nurse123` (Triage Nurse - intake & assign to doctor)
        - **Lab Tech**: `tech_onahi` / `tech123` (Technician - files pending lab test results)
        - **Administrator**: `admin_idsr` / `admin123` (Registry Specialist - staff attendance & all records)
        ''')
    st.stop()

current_user = st.session_state["current_user"]

with st.sidebar:
    st.title("MediScribe AI")
    st.markdown(f'<div class="user-badge">{current_user["name"]}<br><span style="font-weight: normal; font-size: 0.75rem;">{current_user["role"]} - {current_user["department"]}</span></div>', unsafe_allow_html=True)
    
    if st.button("Log Out", use_container_width=True):
        st.session_state["authenticated"] = False
        st.session_state["current_user"] = None
        st.rerun()

    st.markdown("---")
    
    default_portal_idx = 0
    if "Nurse" in current_user["role"]:
        default_portal_idx = 0
    elif "Physician" in current_user["role"] or "Doctor" in current_user["role"]:
        default_portal_idx = 1
    elif "Technician" in current_user["role"] or "Lab" in current_user["role"]:
        default_portal_idx = 2
    elif "Admin" in current_user["role"] or "Specialist" in current_user["role"]:
        default_portal_idx = 4
    else:
        default_portal_idx = 3

    portal_choice = st.radio(
        "Workflow Portals:",
        ["1. Nurse Intake (Vitals & Assign)",
         "2. Doctor Queue & Review",
         "3. Lab Queue & Results Submission",
         "4. Patient Care Card (Side-by-Side)",
         "5. Admin & Staff Attendance Dashboard",
         "6. Central Database & Report Management",
         "7. Bulk Import & Export Center",
         "8. Clinical Guidance Assistant"],
        index=default_portal_idx
    )

if "1. Nurse Intake" in portal_choice:
    st.markdown('<div class="main-header">Nurse Intake & Triage Portal</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="sub-header">Step 1: Authenticated as <strong>{current_user["name"]}</strong>. Record patient vitals, chief complaint, and assign patient to an attending doctor.</div>', unsafe_allow_html=True)

    with st.form("nurse_intake_form"):
        col_p1, col_p2, col_p3 = st.columns(3)
        with col_p1:
            n_enc_id = st.text_input("Encounter ID (e.g. E0001):", value="E0001")
            n_patient_name = st.text_input("Patient Full Name:", value="Robert Miller")
        with col_p2:
            n_age = st.number_input("Age:", min_value=0, max_value=120, value=58)
            n_gender = st.selectbox("Gender:", ["Male", "Female", "Other"])
        with col_p3:
            n_doc = st.selectbox("Assign to Attending Doctor:", ["Dr. Sarah Smith, MD", "Dr. Ibrahim Musa, MD", "Dr. Jane Odum, MD"])

        st.markdown("---")
        st.subheader("Vital Signs & Initial Triage Assessment")
        col_v1, col_v2, col_v3, col_v4, col_v5 = st.columns(5)
        with col_v1:
            v_bp = st.text_input("Blood Pressure:", value="148/92 mmHg")
        with col_v2:
            v_hr = st.text_input("Heart Rate:", value="88 bpm")
        with col_v3:
            v_temp = st.text_input("Temperature:", value="37.8 C")
        with col_v4:
            v_rr = st.text_input("Respiratory Rate:", value="20 /min")
        with col_v5:
            v_spo2 = st.text_input("SpO2 Oxygen Saturation:", value="95%")

        n_cc = st.text_area("Chief Complaint & Triage Notes:", value="Patient reports exertional chest tightness and shortness of breath for two weeks. Denies diaphoresis or syncope.", height=100)

        nurse_submit_btn = st.form_submit_button("Save Patient Vitals & Assign to Doctor Queue", type="primary", use_container_width=True)

        if nurse_submit_btn:
            vitals_dict = {"BP": v_bp, "HR": v_hr, "Temp": v_temp, "RR": v_rr, "SpO2": v_spo2}
            res = registry.nurse_intake(
                encounter_id=n_enc_id,
                patient_name=n_patient_name,
                patient_age=int(n_age),
                patient_gender=n_gender,
                vitals_dict=vitals_dict,
                chief_complaint=n_cc,
                assigned_doctor=n_doc,
                nurse_name=current_user["name"]
            )
            st.success(f"Encounter {n_enc_id} successfully recorded! Assigned to {n_doc} (Status: Doctor Queue).")

    st.markdown("---")
    st.subheader("Recently Triaged Patients in Registry")
    df_all_rec = registry.get_all_records_df()
    if not df_all_rec.empty:
        st.dataframe(df_all_rec[["id", "source_encounter_id", "author_name", "author_role", "chief_complaint", "updated_at"]].head(10), use_container_width=True)

elif "2. Doctor Queue" in portal_choice:
    st.markdown('<div class="main-header">Doctor Consultation & Lab Review Hub</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="sub-header">Authenticated as <strong>{current_user["name"]}</strong> ({current_user["role"]}). Examine new patients, review returned lab results, and finalize Care Cards.</div>', unsafe_allow_html=True)

    tab_doc_initial, tab_doc_lab_review = st.tabs([
        "Active Consultation & Initial Exam",
        "Returned Lab Results & Final Sign-Off"
    ])

    with tab_doc_initial:
        st.subheader("Step 2A: New Patient Clinical Consultation")
        c_q1, c_q2 = st.columns([1, 1])
        with c_q1:
            queue_filter = st.radio("Queue Filter:", ["My Assigned Patients", "All Active Encounters"], horizontal=True, key="doc_q_filter")

        if queue_filter == "My Assigned Patients":
            if hasattr(registry, "get_encounters_by_doctor"):
                assigned_encounters = registry.get_encounters_by_doctor(current_user["name"])
            else:
                assigned_encounters = []
        else:
            df_all = registry.get_all_records_df()
            assigned_encounters = [{"encounter_id": e, "patient_name": f"Patient {e}", "status": "Active"} for e in df_all["source_encounter_id"].unique()[:20]] if not df_all.empty else []

        if not assigned_encounters:
            st.info(f"No active patients currently in your queue. (Patients assigned to {current_user['name']} will appear here).")
            selected_enc = st.selectbox("Select an existing Encounter ID for demonstration:", ["E0001", "E0002", "E0003"], key="doc_demo_sel")
            p_name_val = "Robert Miller"
        else:
            enc_options = [f"{e['encounter_id']} - {e['patient_name']} (Status: {e.get('status', 'Active')})" for e in assigned_encounters]
            chosen_enc_str = st.selectbox("Select Patient to Examine:", enc_options, key="doc_chosen_sel")
            selected_enc = chosen_enc_str.split(" - ")[0]
            p_match = next((e for e in assigned_encounters if e["encounter_id"] == selected_enc), None)
            p_name_val = p_match["patient_name"] if p_match else "Patient"

        st.markdown("---")
        col_d1, col_d2 = st.columns([1, 1.25])

        with col_d1:
            st.subheader(f"Encounter: {selected_enc} - {p_name_val}")

            st.markdown("**Capture Tools (Click to Engage):**")
            c_o, c_v = st.columns(2)
            with c_o:
                if st.button("Camera / OCR Document", use_container_width=True, key="btn_ocr_d"):
                    st.session_state["show_ocr_drawer"] = not st.session_state["show_ocr_drawer"]
            with c_v:
                if st.button("Hausa / English Voice", use_container_width=True, key="btn_aud_d"):
                    st.session_state["show_audio_drawer"] = not st.session_state["show_audio_drawer"]

            if st.session_state.get("show_ocr_drawer"):
                with st.container():
                    st.markdown("##### Document & Prescription Scanner")
                    cam_mode = st.radio("Camera Mode:", ["Rear Camera (Default for Docs)", "Front Camera", "Upload JPG/PNG"], horizontal=True, key="doc_cam_mode")
                    img_c = None
                    if "Rear" in cam_mode or "Front" in cam_mode:
                        img_c = st.camera_input("Capture Document Photo:", key="doc_cam_stream")
                    else:
                        img_c = st.file_uploader("Upload Document File:", type=["jpg", "png", "jpeg"], key="doc_file_up")

                    if img_c:
                        with st.spinner("Extracting text via OCR..."):
                            ocr_res = ocr_scanner.scan_image(img_c)
                            if ocr_res["success"]:
                                st.session_state["transcript_text"] = ocr_res["text"]
                                st.session_state["show_ocr_drawer"] = False
                                st.success("Extracted text transferred to narrative input!")
                                st.rerun()

            if st.session_state.get("show_audio_drawer"):
                with st.container():
                    st.markdown("##### Speech-to-Text with Hausa Clinical Translation")
                    if st.button("Simulate Hausa Doctor-Patient Dialogue", use_container_width=True, key="btn_sim_hausa_d"):
                        aud_res = audio_transcriber.transcribe_audio(None, language="Hausa")
                        st.session_state["transcript_text"] = aud_res["english_transcript"]
                        st.session_state["show_audio_drawer"] = False
                        st.success("Transcribed and translated into clinical English!")
                        st.rerun()

            doc_narrative = st.text_area(
                "Physician Consultation Notes & Dialogue:",
                value=st.session_state["transcript_text"],
                height=260,
                key="doc_narrative_box"
            )

            if st.button("Synthesize Gold-Standard SOAP & 15-Column Care Card", type="primary", use_container_width=True, key="btn_org_ai_d"):
                with st.spinner("Synthesizing Gold-Standard SOAP Note & 15-Column Clinical Care Card..."):
                    extracted = org_extractor.extract_record(doc_narrative, encounter_id=selected_enc)
                    st.session_state["doc_structured_edit"] = extracted
                    st.success("Gold-Standard SOAP & 15-Column structuring complete! Review and edit fields on the right.")

        with col_d2:
            st.subheader("Structured Clinical Fields (Editable Before Saving)")
            edit_data = st.session_state.get("doc_structured_edit")
            if not edit_data:
                st.info("Click 'Organize Notes with AI' to generate editable structured fields.")
            else:
                with st.form("doctor_review_form"):
                    e_cc = st.text_input("Chief Complaint:", value=edit_data["chief_complaint"])
                    e_hpi = st.text_area("HPI:", value=edit_data["hpi"], height=60)
                    e_pmh = st.text_input("PMH:", value=edit_data["pmh"])
                    e_exam = st.text_input("Physical Exam / Vitals:", value=edit_data["exam"])
                    e_diag = st.text_input("Preliminary Diagnosis:", value=edit_data["final_diagnosis"])
                    e_icd = st.text_input("ICD-10 Code:", value=edit_data["icd10"])
                    e_inv = st.text_input("Investigations to Order (Lab/Imaging):", value=edit_data["investigations"])
                    e_meds = st.text_input("Initial Prescriptions / Meds:", value=edit_data["medications"])
                    e_plan = st.text_input("Treatment Plan:", value=edit_data["treatment_plan"])
                    e_soap = st.text_area("SOAP Note:", value=edit_data["soap_note"], height=70)

                    col_b1, col_b2 = st.columns(2)
                    with col_b1:
                        send_lab_btn = st.form_submit_button("Send Patient to Lab for Tests", type="primary", use_container_width=True)
                    with col_b2:
                        save_direct_btn = st.form_submit_button("Save Notes & Complete Encounter", type="secondary", use_container_width=True)

                    if send_lab_btn or save_direct_btn:
                        save_payload = {
                            "clinical_narrative": doc_narrative,
                            "chief_complaint": e_cc,
                            "hpi": e_hpi,
                            "pmh": e_pmh,
                            "exam": e_exam,
                            "differential": edit_data.get("differential", ""),
                            "final_diagnosis": e_diag,
                            "icd10": e_icd,
                            "investigations": e_inv,
                            "medications": e_meds,
                            "treatment_plan": e_plan,
                            "soap_note": e_soap
                        }
                        to_lab = True if send_lab_btn else False
                        res = registry.doctor_submit_investigation(
                            encounter_id=selected_enc,
                            structured_data=save_payload,
                            send_to_lab=to_lab,
                            doctor_name=current_user["name"]
                        )
                        st.success(f"Investigation saved! Status: {res['status']}. Patient forwarded to Lab Queue.")

    # TAB 2: LAB RESULTS REVIEW & FINAL SIGN-OFF
    with tab_doc_lab_review:
        st.subheader("Step 2B: Review Returned Lab Results & Final Decision Support")
        st.caption("Inspect laboratory findings, view AI diagnostic suggestions, update Care Card, and finalize the patient encounter.")

        if hasattr(registry, "get_encounters_ready_for_doctor_review"):
            ready_for_review = registry.get_encounters_ready_for_doctor_review(current_user["name"])
        else:
            ready_for_review = []

        if not ready_for_review:
            st.info(f"No returned lab results pending your review right now. (When the lab files results for your patients, they appear here).")
            rev_enc_choice = st.selectbox("Select encounter to inspect returned results for demonstration:", ["E0001", "E0100", "E0002"], key="rev_demo_sel")
        else:
            st.markdown(f"**Patients with Returned Lab Results ({len(ready_for_review)}):**")
            rev_options = [f"{e['encounter_id']} - {e['patient_name']}" for e in ready_for_review]
            rev_choice_str = st.selectbox("Select Patient to Review Lab Results:", rev_options, key="rev_choice_sel")
            rev_enc_choice = rev_choice_str.split(" - ")[0]

        care_card_data = registry.get_care_card(rev_enc_choice)
        e_meta = care_card_data.get("encounter", {})
        i_inv = care_card_data.get("initial_investigation", {})
        u_rep = care_card_data.get("updated_report", {})

        st.markdown("---")
        # Top comparison summary
        c_r1, c_r2 = st.columns(2)
        with c_r1:
            st.markdown("##### Doctor Initial Notes (Pre-Lab)")
            if i_inv:
                st.info(f"**Preliminary Diagnosis**: `{i_inv.get('final_diagnosis')}` (ICD-10: `{i_inv.get('icd10')}`)\n\n**Ordered Tests**: {i_inv.get('investigations')}\n\n**Exam**: {i_inv.get('exam')}")
            else:
                st.info("Initial assessment recorded.")
        with c_r2:
            st.markdown("##### Returned Lab Findings (Post-Lab)")
            if u_rep:
                st.success(f"**Lab Findings**: {u_rep.get('investigations', e_meta.get('lab_results', 'Lab complete'))}\n\n**Confirmed Diagnosis**: `{u_rep.get('final_diagnosis')}` (ICD-10: `{u_rep.get('icd10')}`)\n\n**Technician**: {u_rep.get('author_name')}")
            else:
                st.warning("Lab report pending submission.")

        st.markdown("---")
        st.subheader("AI Decision Support & Clinical Interpretation")
        
        # Clinical AI Decision Support Generator based on findings
        lab_text_val = u_rep.get("investigations", "") if u_rep else "Malaria RDT Positive"
        diag_suggested = u_rep.get("final_diagnosis", "Malaria") if u_rep else "Malaria"
        icd_suggested = u_rep.get("icd10", "B54") if u_rep else "B54"

        ai_rec_text = f"**AI Clinical Insight**: Laboratory findings confirm **{diag_suggested}** (ICD-10: **{icd_suggested}**).\n- *Recommended First-Line Therapy*: Artemisinin-based Combination Therapy (ACT) / standard protocol.\n- *Patient Monitoring*: Advise full medication adherence and prompt return if symptoms worsen."
        st.info(ai_rec_text)

        st.markdown("---")
        st.subheader("Final Care Card & SOAP Note Sign-Off")
        
        with st.form("doctor_final_signoff_form"):
            col_f1, col_f2 = st.columns(2)
            with col_f1:
                fin_diag = st.text_input("Final Primary Diagnosis:", value=diag_suggested)
                fin_icd = st.text_input("Final ICD-10 Code:", value=icd_suggested)
                fin_disp = st.selectbox("Discharge Disposition:", ["Discharged Home with Prescription", "Admitted for Inpatient Observation", "Referred to Specialist Clinic"])
            with col_f2:
                fin_meds = st.text_input("Final Prescribed Medications:", value="Artemether-Lumefantrine 80/480mg PO BID x 3 days with food; Paracetamol 1g PRN")
                fin_plan = st.text_input("Comprehensive Treatment & Discharge Plan:", value="Complete 3-day ACT course. Maintain hydration. Return if fever persists beyond 72 hours.")

            default_fin_soap = f"S: Patient presented with {i_inv.get('chief_complaint', 'fever')}. O: Exam: {i_inv.get('exam', 'vitals stable')}; Lab Results: {lab_text_val}. A: Confirmed {fin_diag} (ICD-10: {fin_icd}). P: {fin_meds}. Disposition: {fin_disp}."
            fin_soap = st.text_area("Finalized Comprehensive SOAP Note:", value=default_fin_soap, height=90)

            if st.form_submit_button("Approve, Sign-Off & Finalize Patient Care Card", type="primary", use_container_width=True):
                res_fin = registry.doctor_finalize_encounter(
                    encounter_id=rev_enc_choice,
                    final_diagnosis=fin_diag,
                    final_icd10=fin_icd,
                    final_medications=fin_meds,
                    final_treatment_plan=fin_plan,
                    final_soap_note=fin_soap,
                    discharge_disposition=fin_disp,
                    doctor_name=current_user["name"]
                )
                st.success(f"Encounter {rev_enc_choice} successfully finalized by {current_user['name']}! Marked as '{res_fin['status']}'.")
                st.rerun()

elif "3. Lab Queue" in portal_choice:
    st.markdown('<div class="main-header">Laboratory Results Submission Portal</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="sub-header">Step 3: Authenticated as <strong>{current_user["name"]}</strong>. Receive ordered tests, file lab findings, and update patient record.</div>', unsafe_allow_html=True)

    pending_labs = registry.get_pending_lab_encounters()

    if not pending_labs:
        st.info("No encounters currently pending lab results. (Doctors send patients here after consultation).")
        lab_enc_choice = st.selectbox("Select encounter to submit lab results for demonstration:", ["E0001", "E0002", "E0003"])
    else:
        st.markdown(f"**Encounters in Pending Lab Queue ({len(pending_labs)}):**")
        lab_options = [f"{e['encounter_id']} - {e['patient_name']}" for e in pending_labs]
        lab_enc_str = st.selectbox("Select Patient to File Results:", lab_options)
        lab_enc_choice = lab_enc_str.split(" - ")[0]

    care_card_prev = registry.get_care_card(lab_enc_choice)
    init_inv = care_card_prev.get("initial_investigation", {})

    st.markdown("---")
    col_l1, col_l2 = st.columns([1, 1.2])

    with col_l1:
        st.subheader("Ordered Investigations (Doctor Note)")
        if init_inv:
            st.info(f"**Ordered Tests**: {init_inv.get('investigations', 'Malaria RDT; FBC; Urinalysis')}")
            st.markdown(f"**Preliminary Diagnosis**: `{init_inv.get('final_diagnosis', 'N/A')}` (ICD-10: `{init_inv.get('icd10', 'N/A')}`)")
            st.markdown(f"**Doctor Exam Notes**: {init_inv.get('exam', 'Vitals recorded')}")
        else:
            st.info("Ordered Tests: Malaria RDT; Full Blood Count; Peak flow evaluation")

    with col_l2:
        st.subheader("Submit Diagnostic Results")
        with st.form("lab_results_form"):
            lab_findings = st.text_area("Laboratory Test Findings & Values:", value="Malaria RDT: Positive (+); FBC: Hb 11.4 g/dL, WBC 7.2 x10^9/L. Platelets normal.", height=100)
            conf_diag = st.text_input("Confirmed Diagnosis (Post-Lab):", value="Malaria")
            conf_icd = st.text_input("Confirmed ICD-10 Code:", value="B54")

            if st.form_submit_button("Submit Lab Report to Central Registry", type="primary", use_container_width=True):
                res = registry.lab_submit_results(
                    encounter_id=lab_enc_choice,
                    lab_results_text=lab_findings,
                    confirmed_diagnosis=conf_diag,
                    confirmed_icd10=conf_icd,
                    lab_tech_name=current_user["name"]
                )
                st.success(f"Lab results successfully filed for {lab_enc_choice}! Care Card updated side-by-side.")

elif "4. Patient Care Card" in portal_choice:
    st.markdown('<div class="main-header">Patient Care Card - Side-by-Side Clinical View</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Step 4: Compares Doctor Initial Investigation side-by-side with the Updated Lab Report without overwriting.</div>', unsafe_allow_html=True)

    df_all_encs = registry.get_all_records_df()
    enc_list_all = list(df_all_encs["source_encounter_id"].unique()) if not df_all_encs.empty and "source_encounter_id" in df_all_encs.columns else ["E0001"]
    
    col_c1, col_c2 = st.columns([2, 1])
    with col_c1:
        care_enc = st.selectbox("Select Patient Encounter to View Care Card:", enc_list_all)

    care_data = registry.get_care_card(care_enc)
    enc_meta = care_data.get("encounter", {})
    init_inv = care_data.get("initial_investigation", {})
    updated_rep = care_data.get("updated_report", {})

    st.markdown("---")
    
    status_label = enc_meta.get("status", "Completed")
    badge_cls = "stage-completed" if status_label == "Completed" else "stage-doctor"
    st.markdown(f'''
    <div class="card-box">
        <span class="stage-badge {badge_cls}">{status_label.upper()}</span>
        <strong style="font-size: 1.15rem; color: #1E3A8A;">Encounter {care_enc} - {enc_meta.get("patient_name", "Patient")}</strong>
        <p style="margin-top: 6px; margin-bottom: 0; color: #4B5563; font-size: 0.9rem;">
            <strong>Age/Gender:</strong> {enc_meta.get("patient_age", "Adult")} {enc_meta.get("patient_gender", "")} | 
            <strong>Assigned Doctor:</strong> {enc_meta.get("assigned_doctor", "Dr. Sarah Smith, MD")} | 
            <strong>Nurse Vitals:</strong> {enc_meta.get("nurse_vitals", "BP 148/92, HR 88")}
        </p>
    </div>
    ''', unsafe_allow_html=True)

    col_left_card, col_right_card = st.columns(2)

    with col_left_card:
        st.markdown("### Initial Investigation (Doctor Note)")
        st.caption("Doctor structured assessment before laboratory tests.")
        if init_inv:
            st.markdown(f"**Author**: `{init_inv.get('author_name', 'Dr. Sarah Smith, MD')}` (`{init_inv.get('author_role', 'Physician')}`)")
            st.markdown(f"**Chief Complaint**: {init_inv.get('chief_complaint', 'N/A')}")
            st.markdown(f"**HPI**: {init_inv.get('hpi', 'N/A')}")
            st.markdown(f"**Physical Exam / Vitals**: {init_inv.get('exam', 'N/A')}")
            st.markdown(f"**Preliminary Diagnosis**: `{init_inv.get('final_diagnosis', 'N/A')}` (ICD-10: `{init_inv.get('icd10', 'N/A')}`)")
            st.markdown(f"**Ordered Tests**: {init_inv.get('investigations', 'N/A')}")
            st.markdown(f"**Initial Prescriptions**: {init_inv.get('medications', 'N/A')}")
            st.markdown("**SOAP Summary**:")
            st.info(init_inv.get("soap_note", "No SOAP note recorded"))
        else:
            st.info("No Initial Investigation recorded yet.")

    with col_right_card:
        st.markdown("### Updated Report (Post-Lab Findings)")
        st.caption("Updated clinical report incorporating laboratory confirmation.")
        if updated_rep and updated_rep != init_inv:
            st.markdown(f"**Author**: `{updated_rep.get('author_name', 'Onahi Emmanuel, Tech')}` (`{updated_rep.get('author_role', 'Technician')}`)")
            st.markdown(f"**Chief Complaint**: {updated_rep.get('chief_complaint', 'N/A')}")
            st.markdown(f"**HPI**: {updated_rep.get('hpi', 'N/A')}")
            st.markdown(f"**Exam & Lab Findings**: {updated_rep.get('exam', 'N/A')}")
            st.markdown(f"**Confirmed Diagnosis**: `{updated_rep.get('final_diagnosis', 'N/A')}` (ICD-10: `{updated_rep.get('icd10', 'N/A')}`)")
            st.markdown(f"**Completed Tests**: {updated_rep.get('investigations', 'N/A')}")
            st.markdown(f"**Final Medication Plan**: {updated_rep.get('medications', 'N/A')}")
            st.markdown("**SOAP Summary**:")
            st.success(updated_rep.get("soap_note", "No SOAP note recorded"))
        else:
            st.warning("Lab results pending. Once the lab technician files test results, they will appear here side-by-side.")

    st.markdown("---")
    st.subheader("15-Column Standard Schema View (Exact match for track2_organizer_dataset.csv)")
    all_vars = care_data.get("all_variants", [])
    if all_vars:
        df_vars = pd.DataFrame(all_vars)
        st.dataframe(df_vars, use_container_width=True)

elif "5. Admin & Staff Attendance" in portal_choice:
    st.markdown('<div class="main-header">Administrator Operations & Staff Attendance Hub</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="sub-header">Central oversight of clinical personnel attendance, patient allocations, and system audit logs. Active Admin: <strong>{current_user["name"]}</strong>.</div>', unsafe_allow_html=True)

    df_all_rec = registry.get_all_records_df()
    df_audit_all = registry.get_audit_logs_df()

    k1, k2, k3, k4 = st.columns(4)
    with k1:
        st.metric("Total Records Ingested", len(df_all_rec))
    with k2:
        st.metric("Unique Patient Encounters", df_all_rec["source_encounter_id"].nunique() if not df_all_rec.empty else 0)
    with k3:
        st.metric("Active Staff Members", df_audit_all["editor_name"].nunique() if not df_audit_all.empty else 0)
    with k4:
        st.metric("Total Audit Actions", len(df_audit_all))

    st.markdown("---")
    st.subheader("Staff Member Attendance & Function Ledger")
    st.caption("Detailed record of who (staff member), which function/stage, and which patient encounter was attended to.")

    if not df_audit_all.empty:
        staff_summary = df_audit_all.groupby(["editor_name", "action"]).agg(
            total_actions=("record_id", "count"),
            patients_attended=("record_id", lambda x: ", ".join(list(dict.fromkeys(x))[:5]) + ("..." if len(dict.fromkeys(x)) > 5 else ""))
        ).reset_index()

        st.dataframe(staff_summary, use_container_width=True)

        st.markdown("---")
        st.subheader("Filter Complete Audit Trail by Staff / Action")
        c_a1, c_a2 = st.columns(2)
        with c_a1:
            staff_filter = st.selectbox("Filter by Staff Name:", ["All Staff"] + list(df_audit_all["editor_name"].unique()))
        with c_a2:
            action_filter = st.selectbox("Filter by Action / Stage:", ["All Actions"] + list(df_audit_all["action"].unique()))

        filtered_audit = df_audit_all.copy()
        if staff_filter != "All Staff":
            filtered_audit = filtered_audit[filtered_audit["editor_name"] == staff_filter]
        if action_filter != "All Actions":
            filtered_audit = filtered_audit[filtered_audit["action"] == action_filter]

        st.dataframe(filtered_audit, use_container_width=True)
    else:
        st.info("No audit entries recorded yet.")

    st.markdown("---")
    st.subheader("Disease & ICD-10 Epidemiology Distribution")
    if not df_all_rec.empty and "final_diagnosis" in df_all_rec.columns:
        diag_counts = df_all_rec["final_diagnosis"].value_counts().reset_index()
        diag_counts.columns = ["Diagnosis", "Patient Count"]
        st.dataframe(diag_counts, use_container_width=True)

elif "6. Central Database" in portal_choice:
    st.markdown('<div class="main-header">Central Database & Report Management Hub</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="sub-header">Universal search, multi-criteria filtering, and in-place report management. Authenticated as <strong>{current_user["name"]}</strong>.</div>', unsafe_allow_html=True)

    c_s1, c_s2 = st.columns([2, 1])
    with c_s1:
        search_query = st.text_input("Universal Search (Keyword, Condition, Medication, Patient, ID, Author):", placeholder="e.g. Malaria, Salbutamol, E0001, Tech Onahi...")

    df_all = registry.get_all_records_df()
    
    col_f1, col_f2, col_f3, col_f4 = st.columns(4)
    with col_f1:
        enc_list = ["All"] + list(df_all["source_encounter_id"].unique()) if not df_all.empty and "source_encounter_id" in df_all.columns else ["All"]
        filter_enc = st.selectbox("Encounter ID:", enc_list)
    with col_f2:
        diag_list = ["All"] + list(df_all["final_diagnosis"].dropna().unique()) if not df_all.empty and "final_diagnosis" in df_all.columns else ["All"]
        filter_diag = st.selectbox("Diagnosis:", diag_list)
    with col_f3:
        icd_list = ["All"] + list(df_all["icd10"].dropna().unique()) if not df_all.empty and "icd10" in df_all.columns else ["All"]
        filter_icd = st.selectbox("ICD-10 Code:", icd_list)
    with col_f4:
        role_col = "author_role" if "author_role" in df_all.columns else None
        role_list = ["All"] + list(df_all[role_col].dropna().unique()) if role_col and not df_all.empty else ["All"]
        filter_role = st.selectbox("Author Role:", role_list)

    filtered_df = registry.search_and_filter(
        search_query=search_query,
        encounter_id=filter_enc,
        diagnosis=filter_diag,
        icd10=filter_icd,
        role=filter_role
    )

    st.markdown("---")
    st.markdown(f"**Displaying {len(filtered_df)} of {len(df_all)} Total Records**")
    
    if filtered_df.empty:
        st.info("No records matching your search/filter criteria.")
    else:
        st.dataframe(filtered_df, use_container_width=True, height=300)

        st.markdown("---")
        st.subheader("Manage Selected Patient Report")
        record_options = list(filtered_df["id"].unique()) if "id" in filtered_df.columns else []
        if record_options:
            selected_record_id = st.selectbox("Select Record ID to Inspect / Edit / Delete:", record_options)
            if selected_record_id:
                row_data = filtered_df[filtered_df["id"] == selected_record_id].iloc[0]
                with st.expander(f"Inspect & Edit Record: {selected_record_id}", expanded=True):
                    with st.form("edit_record_form"):
                        c1, c2 = st.columns(2)
                        with c1:
                            edit_cc = st.text_input("Chief Complaint:", value=str(row_data.get("chief_complaint", "")))
                            edit_hpi = st.text_area("HPI:", value=str(row_data.get("hpi", "")), height=70)
                            edit_exam = st.text_input("Exam Findings:", value=str(row_data.get("exam", "")))
                        with c2:
                            edit_diag = st.text_input("Final Diagnosis:", value=str(row_data.get("final_diagnosis", "")))
                            edit_icd = st.text_input("ICD-10 Code:", value=str(row_data.get("icd10", "")))
                            edit_meds = st.text_input("Medications:", value=str(row_data.get("medications", "")))
                        edit_soap = st.text_area("SOAP Note:", value=str(row_data.get("soap_note", "")), height=70)

                        col_sv, col_dl = st.columns(2)
                        with col_sv:
                            if st.form_submit_button("Save Changes", type="primary", use_container_width=True):
                                registry.update_record(selected_record_id, {"chief_complaint": edit_cc, "hpi": edit_hpi, "exam": edit_exam, "final_diagnosis": edit_diag, "icd10": edit_icd, "medications": edit_meds, "soap_note": edit_soap}, editor_name=current_user["name"])
                                st.success("Updated successfully!")
                                st.rerun()
                        with col_dl:
                            if st.form_submit_button("Delete Record", type="secondary", use_container_width=True):
                                registry.delete_record(selected_record_id, editor_name=current_user["name"])
                                st.warning("Deleted record.")
                                st.rerun()

elif "7. Bulk Import" in portal_choice:
    st.markdown('<div class="main-header">Bulk Data Ingestion & Export Center</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Upload multi-patient spreadsheets with auto-structuring, and export 15-column files matching track2_organizer_dataset.csv.</div>', unsafe_allow_html=True)

    tab_import, tab_export, tab_audit = st.tabs(["Bulk Data Import", "Universal Data Export", "System Audit Logs"])

    with tab_import:
        st.subheader("Bulk Import Clinical Reports (CSV or Excel)")
        sample_btn = st.button("Load Organizer Dataset Sample (500 records from track2_organizer_dataset.csv)", type="secondary")
        if sample_btn:
            organizer_path = "/home/Onahi/Devdir/hack/data/raw/track2_organizer_dataset.csv"
            if os.path.exists(organizer_path):
                with st.spinner("Importing records..."):
                    df_sample = pd.read_csv(organizer_path).head(500)
                    count = registry.bulk_import_dataframe(df_sample, author_name=current_user["name"], author_role=current_user["role"])
                    st.success(f"Successfully loaded {count} records into Central Database!")
                    st.rerun()

        st.markdown("---")
        up_f = st.file_uploader("Upload custom CSV/Excel:", type=["csv", "xlsx", "xls"])
        if up_f:
            df_up = pd.read_csv(up_f) if up_f.name.endswith(".csv") else pd.read_excel(up_f)
            st.dataframe(df_up.head(5), use_container_width=True)
            if st.button(f"Confirm & Ingest All {len(df_up)} Records", type="primary"):
                count = registry.bulk_import_dataframe(df_up, author_name=current_user["name"], author_role=current_user["role"])
                st.success(f"Ingested {count} records!")
                st.rerun()

    with tab_export:
        st.subheader("Universal 15-Column Export")
        df_all = registry.get_all_records_df()
        st.download_button(
            label="Download Standardized 15-Column CSV",
            data=df_all.to_csv(index=False).encode('utf-8'),
            file_name="central_clinical_registry_export.csv",
            mime="text/csv",
            type="primary",
            use_container_width=True
        )

    with tab_audit:
        st.subheader("Database Audit Trail")
        st.dataframe(registry.get_audit_logs_df(), use_container_width=True)

elif "8. Clinical Guidance" in portal_choice:
    st.markdown('<div class="main-header">Clinical Guidance & Case Recall Assistant</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Interactive assistant for disease definitions, treatment guidelines, and Central Database record recall.</div>', unsafe_allow_html=True)

    for msg in st.session_state["chat_history"]:
        if msg["role"] == "user":
            st.chat_message("user").write(msg["content"])
        else:
            st.chat_message("assistant").write(msg["content"])

    user_query = st.chat_input("Ask a clinical question or recall an encounter (e.g. 'Recall encounter E0001'):")
    if user_query:
        st.session_state["chat_history"].append({"role": "user", "content": user_query})
        st.chat_message("user").write(user_query)

        q_low = user_query.lower()
        if "recall" in q_low or "e00" in q_low:
            df_all = registry.get_all_records_df()
            matched = False
            for enc_val in df_all["source_encounter_id"].unique():
                if enc_val.lower() in q_low:
                    rows = df_all[df_all["source_encounter_id"] == enc_val]
                    bot_reply = f"**Found {len(rows)} report variant(s) for Encounter {enc_val}:**\n\n"
                    for _, r in rows.iterrows():
                        bot_reply += f"- **Variant {r['variant_id']} (Type: {r.get('report_type', 'Note')})**: Diagnosis: `{r['final_diagnosis']}` (ICD-10: `{r['icd10']}`)\n  - *SOAP*: {r['soap_note']}\n\n"
                    matched = True
                    break
            if not matched:
                bot_reply = "I checked the Central Database. Could you please specify the exact Encounter ID (e.g. E0001, E0010)?"
        elif "malaria" in q_low:
            bot_reply = "**Malaria Clinical Protocol (ICD-10: B54)**:\n- *Case Definition*: Acute fever with positive RDT/microscopy.\n- *Treatment*: Artemisinin-based Combination Therapy (ACT).\n- *Red Flags*: Impaired consciousness, severe anemia, respiratory distress."
        else:
            bot_reply = f"Clinical query received: '{user_query}'. Ensure all vitals and negative findings are documented."

        st.session_state["chat_history"].append({"role": "assistant", "content": bot_reply})
        st.chat_message("assistant").write(bot_reply)

st.markdown('''
<div class="mobile-bottom-nav">
    <div class="nav-item">Nurse</div>
    <div class="nav-item">Doctor</div>
    <div class="nav-item">Lab</div>
    <div class="nav-item">Care Card</div>
</div>
''', unsafe_allow_html=True)
