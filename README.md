# Dhaka College HSC Result Analysis & Processing System

A modular repository containing data processing pipelines, web dashboards, scrapers, and datasets for analyzing **Dhaka College HSC Examination Results (2026 Batch / Session 2024–2025)**.

---

## Repository Structure

```
.
├── dhaka_hsc_2026_107977.pdf       # Official Dhaka Education Board HSC 2026 result gazette (EIIN: 107977)
├── hsc result humanities/          # Humanities student profiles, Year 2 candidate rolls, & board results
├── hsc result science/             # Science student data, Form fill-up receipt scraper, & roll mapping
├── python_captcha/                 # Education Board marksheet scraper with OCR captcha solver & web UI
├── DCAnalyticsV2/                  # Dhaka College Analytics web application (React + Vite + Tailwind)
├── EDUBOARDBD/                     # Go-based CLI tool for education board result scraping
└── docs/                           # Reverse engineering captures, API documentation, & security audits
```

---

## Directories & Modules

### 1. [`hsc result humanities/`](file:///home/mushfiq/Desktop/DC_Result/hsc%20result%20humanities)
Contains scraped student profile data and filtered rolls for **HSC Humanities (Session 2024–2025)**:
- **`rolls.json` / `humanities_year2_rolls.json`**: List of **143** college rolls in Academic Year 2 (eligible HSC examinees).
- **`humanities_students_year2.json`**: Detailed JSON dataset for all 143 Year 2 students (names, subjects, photos, sessions).
- **`humanities_students_year1.json`**: The 6 students who remained in Academic Year 1.
- **`humanities_all_students.json`**: Full dataset of all 149 valid Humanities profiles for the 2024–2025 session.
- **`board_results_humanities_2026.json`**: Official board grades parsed from `dhaka_hsc_2026_107977.pdf` (148 examinees).
- **`fetch_humanities_rolls.py`**: Automated script to query the Dhaka College eShiksa controller API and rebuild the dataset.

### 2. [`hsc result science/`](file:///home/mushfiq/Desktop/DC_Result/hsc%20result%20science)
Complete batch processing pipeline and datasets for **HSC Science (Session 2024–2025)**:
- **`assigned_hsc_rolls_862.json`**: Full roster of 862 Year 2 candidates mapped to Dhaka Board HSC rolls (`108727`–`109579`).
- **`assigned_hsc_rolls_853.json`**: The 853 candidates who completed Form fill-up payments.
- **`unpaid_science_students.json`**: The 9 candidates with missing or unpaid Form fill-up receipts.
- **`receipts/`**: Over 850 downloaded payment receipt PDFs.
- **`scrape_receipts.py`**: Scrapes transaction payment records from Dhaka College portal.
- **`extract_registrations.py`**: Extracts registration numbers and applicant metadata from PDF receipts.
- **`assign_new_rolls.py`**: Maps college class rolls to board exam rolls using anchor points and payment chronology.

### 3. [`python_captcha/`](file:///home/mushfiq/Desktop/DC_Result/python_captcha)
Automated marksheet scraper and lightweight client-side results dashboard:
- **`eduboard_fetch.py`**: Queries the official Education Board results service with OCR-based automated captcha solving.
- **`captcha_ocr.py` / `captcha_digits.py`**: Computer vision and digit segmentation algorithms for solving captchas.
- **`recover_missing_rolls.py`**: Failure recovery and re-query pipeline for missing rolls.
- **`build_web_data.py`**: Builds optimized `students_data.json` for frontend consumption.
- **`index.html` / `app.js` / `styles.css`**: Standalone web UI for searching and filtering marksheets and merit rankings.

### 4. [`DCAnalyticsV2/`](file:///home/mushfiq/Desktop/DC_Result/DCAnalyticsV2)
Production-grade analytics platform built with React, Vite, and Tailwind CSS:
- Exam manager and merit list visualizer.
- Class-wide and group-wise comparative analytics.
- Section-based heuristic mapping and student directory.

### 5. [`EDUBOARDBD/`](file:///home/mushfiq/Desktop/DC_Result/EDUBOARDBD)
High-performance Go CLI utility for querying Bangladesh Education Board web results.

### 6. [`docs/`](file:///home/mushfiq/Desktop/DC_Result/docs)
Technical documentation and research:
- `dhakacollege_post_requests.md`: Network inspection logs and payload formats for `controller_student_module.php`.
- `security-assessment-educationboardresults-v2.md`: Comprehensive security evaluation of Education Board results endpoint.
- `promt.txt`: Historical specification and scraping requirements.

---

## Official Gazette Source

- **[`dhaka_hsc_2026_107977.pdf`](file:///home/mushfiq/Desktop/DC_Result/dhaka_hsc_2026_107977.pdf)**: Official result publication for Dhaka College (EIIN 107977) by the Board of Intermediate & Secondary Education, Dhaka.
