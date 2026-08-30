# Hackathon Documentation Directory (`doc/`)

This directory contains the central architectural documentation, implementation guides, whitepaper PDFs, walkthroughs, activity logs, and presentation assets for **Track 2: AI-Assisted Clinical Documentation & Central Registry** (ISS 2026 AI Hackathon).

---

## Master Whitepaper & System PDFs
* [doc/MediScribe_AI_System_Documentation.pdf](file:///kali-linux/home/Onahi/Devdir/hack/doc/MediScribe_AI_System_Documentation.pdf) - **Full System Technical Whitepaper & Complete Documentation (PDF)**.
* [doc/track_2_clinical_documentation_whitepaper.pdf](file:///kali-linux/home/Onahi/Devdir/hack/doc/track_2_clinical_documentation_whitepaper.pdf) - **Track 2 Clinical Documentation Whitepaper (PDF)**.

---

## Directory Navigation

### 1. Master System & Architecture Documentation
* [doc/implementations/comprehensive_system_documentation.md](file:///kali-linux/home/Onahi/Devdir/hack/doc/implementations/comprehensive_system_documentation.md) - Master technical and functional documentation detailing all system features, data flows, and module references.
* [doc/implementations/comprehensive_model_evaluation_and_selection.md](file:///kali-linux/home/Onahi/Devdir/hack/doc/implementations/comprehensive_model_evaluation_and_selection.md) - Deep-dive evaluation on whether a single model can handle the 15-column organizer dataset, comparative analysis of MedGemma 4B, FLAN-T5, Sublinear TF-IDF + Naive Bayes, and Cloud APIs.
* [doc/implementations/organizer_dataset_analysis_and_central_system_design.md](file:///kali-linux/home/Onahi/Devdir/hack/doc/implementations/organizer_dataset_analysis_and_central_system_design.md) - Statistical breakdown of `track2_organizer_dataset.csv` (5,000 records across 500 encounters) and multi-party variant ledger design.
* [doc/implementations/architecture_and_components.md](file:///kali-linux/home/Onahi/Devdir/hack/doc/implementations/architecture_and_components.md) - Technical component breakdown (Cleaners, Segmenters, Entity Extractor, SOAP Generator, Classifier, LLM Engine).

### 2. Strategic Plans & Track Briefs
* [doc/plans/track_2_clinical_documentation_brief.md](file:///kali-linux/home/Onahi/Devdir/hack/doc/plans/track_2_clinical_documentation_brief.md) - Hackathon track analysis, alignment strategy, and preparation checklist.
* [doc/track_2_brief.html](file:///kali-linux/home/Onahi/Devdir/hack/doc/track_2_brief.html) & [doc/index.html](file:///kali-linux/home/Onahi/Devdir/hack/doc/index.html) - Standalone self-contained HTML presentation with live Cloudflare tunnel and embedded QR code (Served on `http://localhost:8088`).

### 3. Walkthroughs & Quickstart Guides
* [doc/walkthroughs/quickstart_and_verification.md](file:///kali-linux/home/Onahi/Devdir/hack/doc/walkthroughs/quickstart_and_verification.md) - Quickstart execution guide, verification instructions, and test commands.

### 4. Activity & Decision Logs
* [doc/logs/activity_log.md](file:///kali-linux/home/Onahi/Devdir/hack/doc/logs/activity_log.md) - Chronological log recording all actions, decisions, and system updates.

### 5. Media & Demo Assets
* [doc/qrcode_tunnel.png](file:///kali-linux/home/Onahi/Devdir/hack/doc/qrcode_tunnel.png) - High-resolution scannable QR code for the live mobile tunnel demo (`https://gain-officially-grade-gardens.trycloudflare.com/`).
* [doc/qrcode_ascii.txt](file:///kali-linux/home/Onahi/Devdir/hack/doc/qrcode_ascii.txt) - ASCII QR code for terminal display.