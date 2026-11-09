#!/usr/bin/env python3
"""
Extract SSC/HSC Registration Numbers, parent names, admission roll, and phone
from downloaded Humanities payment receipt PDFs via pdftotext.
"""

import json
import os
import re
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
RECEIPTS_DIR = os.path.join(BASE_DIR, "receipts")
ALL_STUDENTS_JSON = os.path.join(BASE_DIR, "humanities_all_students.json")
CHECKPOINT_FILE = os.path.join(BASE_DIR, "scrape_checkpoint.json")
OUTPUT_MAP_JSON = os.path.join(BASE_DIR, "roll_registration_map.json")
OUTPUT_DETAILED_JSON = os.path.join(BASE_DIR, "receipt_extracted_details.json")


def extract_from_pdf(pdf_path: str) -> dict:
    res = subprocess.run(
        ["pdftotext", "-layout", pdf_path, "-"],
        capture_output=True,
        text=True,
        check=True
    )
    text = res.stdout

    def match_pattern(pattern):
        m = re.search(pattern, text)
        return m.group(1).strip() if m else None

    class_roll = match_pattern(r"Class Roll:\s*(\d+)")
    reg_no = match_pattern(r"SSC/HSC Reg\. No\.:\s*(\d+)")
    admission_roll = match_pattern(r"Admission Roll:\s*(\d+)")
    phone = match_pattern(r"Student Phone:\s*(\d+)")
    student_name = match_pattern(r"Student Name:\s*(.+?)\s{2,}Admission Roll:")
    father_name = match_pattern(r"Father's Name:\s*(.+?)\s{2,}Class Roll:")
    mother_name = match_pattern(r"Mother's Name:\s*(.+?)\s{2,}SSC/HSC Reg\. No\.:")
    session = match_pattern(r"Session:\s*([0-9-]+)")
    academic_year = match_pattern(r"Academic Year:\s*(\d+)")

    return {
        "class_roll": class_roll,
        "registration_no": reg_no,
        "student_name": student_name,
        "father_name": father_name,
        "mother_name": mother_name,
        "admission_roll": admission_roll,
        "phone": phone,
        "receipt_session": session,
        "receipt_academic_year": academic_year,
    }


def main():
    with open(ALL_STUDENTS_JSON, "r", encoding="utf-8") as f:
        students = json.load(f)

    ckpt = {}
    if os.path.exists(CHECKPOINT_FILE):
        with open(CHECKPOINT_FILE, "r", encoding="utf-8") as f:
            ckpt = json.load(f)

    students_sorted = sorted(students, key=lambda x: int(x["roll"]))
    extracted_by_roll = {}

    def worker(student):
        roll = str(student["roll"]).strip()
        pdf_path = os.path.join(RECEIPTS_DIR, f"{roll}.pdf")
        if not os.path.exists(pdf_path):
            return roll, {"class_roll": roll, "registration_no": None, "error": "pdf_not_found"}
        try:
            info = extract_from_pdf(pdf_path)
            if not info.get("class_roll"):
                info["class_roll"] = roll
            return roll, info
        except Exception as e:
            return roll, {"class_roll": roll, "registration_no": None, "error": str(e)}

    with ThreadPoolExecutor(max_workers=16) as executor:
        futures = [executor.submit(worker, st) for st in students_sorted]
        for fut in as_completed(futures):
            roll, info = fut.result()
            extracted_by_roll[roll] = info

    roll_to_reg_map = {}
    detailed_list = []
    missing_reg = []

    for st in students_sorted:
        roll = str(st["roll"]).strip()
        info = extracted_by_roll.get(roll, {})
        reg_no = info.get("registration_no")
        roll_to_reg_map[roll] = reg_no
        if not reg_no:
            missing_reg.append(roll)

        ck = ckpt.get(roll, {})
        has_ff = bool(ck.get("paid"))

        detailed_entry = dict(st)
        detailed_entry["has_form_fill_up"] = has_ff
        detailed_entry["registration_no"] = reg_no
        detailed_entry["father_name"] = info.get("father_name")
        detailed_entry["mother_name"] = info.get("mother_name")
        detailed_entry["admission_roll"] = info.get("admission_roll")
        detailed_entry["phone"] = info.get("phone")
        detailed_list.append(detailed_entry)

    with open(OUTPUT_MAP_JSON, "w", encoding="utf-8") as f:
        json.dump(roll_to_reg_map, f, ensure_ascii=False, indent=2)

    with open(OUTPUT_DETAILED_JSON, "w", encoding="utf-8") as f:
        json.dump(detailed_list, f, ensure_ascii=False, indent=2)

    print(f"Total PDFs processed: {len(students_sorted)}")
    print(f"Successfully extracted SSC/HSC Reg. No.: {len(students_sorted) - len(missing_reg)}")
    print(f"Missing Reg. No.: {len(missing_reg)} {missing_reg}")
    print(f"Saved roll -> registration map to: {OUTPUT_MAP_JSON}")
    print(f"Saved detailed student records with registration_no to: {OUTPUT_DETAILED_JSON}")


if __name__ == "__main__":
    main()
