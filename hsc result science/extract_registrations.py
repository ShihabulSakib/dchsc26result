import json
import os
import re
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
RECEIPTS_DIR = os.path.join(BASE_DIR, "receipts")
CANDIDATES_862_JSON = os.path.join(BASE_DIR, "potential_exam_candidates_862.json")
OUTPUT_MAP_JSON = os.path.join(BASE_DIR, "roll_registration_map.json")
OUTPUT_DETAILED_JSON = os.path.join(BASE_DIR, "receipt_extracted_details.json")


def extract_from_pdf(pdf_path: str) -> dict:
    """
    Uses pdftotext -layout to extract text from a receipt PDF and parses
    Class Roll, SSC/HSC Reg. No., Student Name, Father's Name, Mother's Name,
    Admission Roll, Student Phone, Fee Type, Amount, and Transaction Date.
    """
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
    with open(CANDIDATES_862_JSON, "r", encoding="utf-8") as f:
        candidates = json.load(f)

    # Sort by college roll ascending for clean, deterministic output
    candidates_sorted = sorted(candidates, key=lambda x: int(x["roll"]))

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
        futures = [executor.submit(worker, st) for st in candidates_sorted]
        for fut in as_completed(futures):
            roll, info = fut.result()
            extracted_by_roll[roll] = info

    # Build clean roll -> registration_no mapping (ordered by college roll)
    roll_to_reg_map = {}
    detailed_list = []
    missing_reg = []

    for st in candidates_sorted:
        roll = str(st["roll"]).strip()
        info = extracted_by_roll.get(roll, {})
        reg_no = info.get("registration_no")
        roll_to_reg_map[roll] = reg_no
        if not reg_no:
            missing_reg.append(roll)

        detailed_entry = dict(st)
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

    print(f"Total PDFs processed: {len(candidates_sorted)}")
    print(f"Successfully extracted SSC/HSC Reg. No.: {len(candidates_sorted) - len(missing_reg)}")
    print(f"Missing Reg. No.: {len(missing_reg)} {missing_reg}")
    print(f"Saved roll -> registration map to: {OUTPUT_MAP_JSON}")
    print(f"Saved detailed student records with registration_no to: {OUTPUT_DETAILED_JSON}")


if __name__ == "__main__":
    main()
