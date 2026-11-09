# HSC Result Science (Dhaka College)

Pipeline, datasets, and extracted fee receipts for **HSC Science (Session 2024–2025)** at Dhaka College.

## Overview

- **Target Department**: HSC - Science
- **Session**: 2024–2025 (HSC 2026 Batch)
- **Total Science Students Scraped**: 1,783 (includes both 2024–2025 and 2025–2026 sessions)
- **Academic Year 2 Examinee Candidates**: **862**
- **Form Fill-Up Paid Examinees**: **853**
- **Unpaid / No Form Fill-Up Receipt**: **9**
- **Assigned HSC Board Rolls**: `108727` to `109579`

---

## Pipeline Scripts

1. [`scrape_receipts.py`](file:///home/mushfiq/Desktop/DC_Result/hsc%20result%20science/scrape_receipts.py): Logs in to Dhaka College eShiksa portal, scans student fee transactions, and downloads "Form fill-up" receipt PDFs into `receipts/`.
2. [`extract_registrations.py`](file:///home/mushfiq/Desktop/DC_Result/hsc%20result%20science/extract_registrations.py): Extracts registration numbers, parent details, phone numbers, and payment details from downloaded PDFs via `pdftotext`.
3. [`assign_new_rolls.py`](file:///home/mushfiq/Desktop/DC_Result/hsc%20result%20science/assign_new_rolls.py): Maps college class rolls to Dhaka Board HSC 2026 exam rolls based on registration batches, payment dates, and anchor validations against the official board gazette (`dhaka_hsc_2026_107977.pdf`).

---

## Key Data Files

| File | Description |
|---|---|
| [`assigned_hsc_rolls_862.json`](file:///home/mushfiq/Desktop/DC_Result/hsc%20result%20science/assigned_hsc_rolls_862.json) | Complete dataset of all 862 candidates with mapped HSC board rolls, board GPA, and registration |
| [`assigned_hsc_rolls_853.json`](file:///home/mushfiq/Desktop/DC_Result/hsc%20result%20science/assigned_hsc_rolls_853.json) | Subset of 853 candidates who paid the Form fill-up fee |
| [`potential_exam_candidates_862.json`](file:///home/mushfiq/Desktop/DC_Result/hsc%20result%20science/potential_exam_candidates_862.json) | The 862 Year 2 candidates before board roll assignment |
| [`science_students.json`](file:///home/mushfiq/Desktop/DC_Result/hsc%20result%20science/science_students.json) | Raw profile scraper output for Science students |
| [`paid_science_students.json`](file:///home/mushfiq/Desktop/DC_Result/hsc%20result%20science/paid_science_students.json) | Profiles with confirmed Form fill-up payment |
| [`unpaid_science_students.json`](file:///home/mushfiq/Desktop/DC_Result/hsc%20result%20science/unpaid_science_students.json) | Detailed records of the 9 unpaid students |
| [`unpaid_rolls.json`](file:///home/mushfiq/Desktop/DC_Result/hsc%20result%20science/unpaid_rolls.json) | List of rolls for unpaid students |
| [`college_to_hsc_roll_map.json`](file:///home/mushfiq/Desktop/DC_Result/hsc%20result%20science/college_to_hsc_roll_map.json) | Direct key-value lookup: `{college_roll: hsc_roll}` |
| [`roll_registration_map.json`](file:///home/mushfiq/Desktop/DC_Result/hsc%20result%20science/roll_registration_map.json) | Direct key-value lookup: `{college_roll: registration_no}` |
| [`receipt_extracted_details.json`](file:///home/mushfiq/Desktop/DC_Result/hsc%20result%20science/receipt_extracted_details.json) | Metadata parsed from receipts |
| [`receipts/`](file:///home/mushfiq/Desktop/DC_Result/hsc%20result%20science/receipts) | Downloaded PDF payment slips |
