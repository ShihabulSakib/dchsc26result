#!/usr/bin/env python3
"""
Assign Dhaka Board HSC 2026 Business Studies exam rolls (455282..455415)
to Dhaka College Business Studies students (Session 2024-2025).
"""

import json
import os
import re
import subprocess

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(BASE_DIR)

DETAILED_INPUT_JSON = os.path.join(BASE_DIR, "receipt_extracted_details.json")
CHECKPOINT_FILE = os.path.join(BASE_DIR, "scrape_checkpoint.json")
BOARD_RESULTS_JSON = os.path.join(BASE_DIR, "board_results_business_2026.json")
BOARD_PDF = os.path.join(PROJECT_ROOT, "dhaka_hsc_2026_107977.pdf")

OUTPUT_PAID_132_JSON = os.path.join(BASE_DIR, "assigned_hsc_rolls_132.json")
OUTPUT_BUSINESS_JSON = os.path.join(BASE_DIR, "assigned_hsc_rolls_business.json")
OUTPUT_ALL_141_JSON = os.path.join(BASE_DIR, "assigned_hsc_rolls_all_141.json")
OUTPUT_ROLL_MAP_JSON = os.path.join(BASE_DIR, "college_to_hsc_roll_map.json")

START_BOARD_ROLL = 455282
TAIL_BOARD_ROLLS = ["455414", "455415"]


def load_board_results() -> dict:
    if os.path.exists(BOARD_RESULTS_JSON):
        with open(BOARD_RESULTS_JSON, "r", encoding="utf-8") as f:
            items = json.load(f)
        return {str(it["board_roll"]).strip(): str(it["result"]).strip() for it in items}

    if not os.path.exists(BOARD_PDF):
        return {}
    res = subprocess.run(
        ["pdftotext", "-layout", BOARD_PDF, "-"],
        capture_output=True,
        text=True,
        check=True
    )
    if ": BUSINESS STUDIES :" not in res.stdout:
        return {}
    bus_text = res.stdout.split(": BUSINESS STUDIES :")[1]
    entries = re.findall(r"(\d{6})\[([^\]]+)\]", bus_text)
    return {r: val.strip() for r, val in entries}


def main():
    with open(DETAILED_INPUT_JSON, "r", encoding="utf-8") as f:
        students = json.load(f)
    with open(CHECKPOINT_FILE, "r", encoding="utf-8") as f:
        ckpt = json.load(f)

    board_results = load_board_results()
    students_sorted = sorted(students, key=lambda x: int(x["roll"]))

    paid_132 = [s for s in students_sorted if s.get("has_form_fill_up")]
    unpaid_9 = [s for s in students_sorted if not s.get("has_form_fill_up")]

    assigned_132 = []
    roll_map = {}

    for idx, st in enumerate(paid_132):
        c_roll = str(st["roll"]).strip()
        hsc_roll = str(START_BOARD_ROLL + idx)
        board_res = board_results.get(hsc_roll)

        e_list = ckpt.get(c_roll, {}).get("entries", [])
        # Find regular form fill-up entry
        ff_entry = next((e for e in e_list if e.get("fee_type") == "Form fill-up"), e_list[0] if e_list else {})

        rec = dict(st)
        rec["serial_no"] = idx + 1
        rec["hsc_roll"] = hsc_roll
        rec["board_gpa_or_status"] = board_res
        rec["form_fillup_date"] = ff_entry.get("tx_date")
        rec["form_fillup_amount"] = ff_entry.get("amount")

        assigned_132.append(rec)
        roll_map[c_roll] = {
            "name": st.get("name"),
            "registration_no": st.get("registration_no"),
            "hsc_roll": hsc_roll,
            "board_gpa_or_status": board_res,
            "has_form_fill_up": True
        }

    # All 141 students list in college roll order
    all_141 = []
    for idx, st in enumerate(students_sorted, 1):
        c_roll = str(st["roll"]).strip()
        e_list = ckpt.get(c_roll, {}).get("entries", [])
        ff_entry = next((e for e in e_list if e.get("fee_type") == "Form fill-up"), e_list[0] if e_list else {})
        hsc_info = roll_map.get(c_roll, {})

        rec = dict(st)
        rec["serial_no"] = idx
        rec["hsc_roll"] = hsc_info.get("hsc_roll")
        rec["board_gpa_or_status"] = hsc_info.get("board_gpa_or_status")
        rec["form_fillup_date"] = ff_entry.get("tx_date") if st.get("has_form_fill_up") else None
        rec["form_fillup_amount"] = ff_entry.get("amount") if st.get("has_form_fill_up") else None
        all_141.append(rec)

    with open(OUTPUT_PAID_132_JSON, "w", encoding="utf-8") as f:
        json.dump(assigned_132, f, ensure_ascii=False, indent=2)

    with open(OUTPUT_BUSINESS_JSON, "w", encoding="utf-8") as f:
        json.dump(assigned_132, f, ensure_ascii=False, indent=2)

    with open(OUTPUT_ALL_141_JSON, "w", encoding="utf-8") as f:
        json.dump(all_141, f, ensure_ascii=False, indent=2)

    with open(OUTPUT_ROLL_MAP_JSON, "w", encoding="utf-8") as f:
        json.dump(roll_map, f, ensure_ascii=False, indent=2)

    print(f"Total students in Business Studies: {len(students_sorted)}")
    print(f"Regular 2nd Year examinees assigned rolls: {len(assigned_132)} ({START_BOARD_ROLL}..{START_BOARD_ROLL + len(assigned_132) - 1})")
    print(f"Tail board rolls in center: {TAIL_BOARD_ROLLS}")
    print(f"Unpaid 1st Year students: {len(unpaid_9)}")
    print(f"Saved: {OUTPUT_BUSINESS_JSON}")


if __name__ == "__main__":
    main()
