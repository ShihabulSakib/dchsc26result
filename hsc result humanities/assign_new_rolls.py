#!/usr/bin/env python3
"""
Assign Dhaka Board HSC 2026 Humanities exam rolls (254880..255026, 900134)
to Dhaka College Humanities students (Session 2024-2025).
"""

import json
import os
import re
import subprocess

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(BASE_DIR)

DETAILED_INPUT_JSON = os.path.join(BASE_DIR, "receipt_extracted_details.json")
CHECKPOINT_FILE = os.path.join(BASE_DIR, "scrape_checkpoint.json")
BOARD_RESULTS_JSON = os.path.join(BASE_DIR, "board_results_humanities_2026.json")
BOARD_PDF = os.path.join(PROJECT_ROOT, "dhaka_hsc_2026_107977.pdf")

OUTPUT_PAID_142_JSON = os.path.join(BASE_DIR, "assigned_hsc_rolls_142.json")
OUTPUT_YEAR2_143_JSON = os.path.join(BASE_DIR, "assigned_hsc_rolls_143.json")
OUTPUT_ALL_149_JSON = os.path.join(BASE_DIR, "assigned_hsc_rolls_149.json")
OUTPUT_ROLL_MAP_JSON = os.path.join(BASE_DIR, "college_to_hsc_roll_map.json")

START_BOARD_ROLL = 254880
TAIL_BOARD_ROLLS = ["255021", "255022", "255023", "255024", "255025", "255026", "900134"]


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
    if ": HUMANITIES :" not in res.stdout:
        return {}
    hum_text = res.stdout.split(": HUMANITIES :")[1].split(": SCIENCE :")[0]
    entries = re.findall(r"(\d{6})\[([^\]]+)\]", hum_text)
    return {r: val.strip() for r, val in entries}


def main():
    with open(DETAILED_INPUT_JSON, "r", encoding="utf-8") as f:
        students = json.load(f)
    with open(CHECKPOINT_FILE, "r", encoding="utf-8") as f:
        ckpt = json.load(f)

    board_results = load_board_results()
    students_sorted = sorted(students, key=lambda x: int(x["roll"]))

    paid_142 = [s for s in students_sorted if s.get("has_form_fill_up")]
    unpaid_7 = [s for s in students_sorted if not s.get("has_form_fill_up")]

    # Model A (Natural College Roll Order among Form fill-up payers, proven by Science progress.jsonl):
    # Wait: in Science, March on-time payers (including 20xxxxxxxx registrations) stayed in natural college roll order,
    # while the single June late payer (15-Jun-2026 / 16-Jun-2026) was placed at the end of the regular block!
    mar_paid = [
        s for s in paid_142
        if "Mar-2026" in ckpt.get(str(s["roll"]), {}).get("entries", [{}])[0].get("tx_date", "")
    ]
    late_paid = [
        s for s in paid_142
        if "Mar-2026" not in ckpt.get(str(s["roll"]), {}).get("entries", [{}])[0].get("tx_date", "")
    ]
    ordered_mar_first = mar_paid + late_paid

    # Model B: Strictly sequential by college roll (including June late payer in college roll spot)
    seq_roll_lookup = {
        str(s["roll"]): str(START_BOARD_ROLL + i)
        for i, s in enumerate(paid_142)
    }

    # Model C: 21xxxxxxxx registrations first, non-21xxxxxxxx at end
    reg_21_paid = [s for s in paid_142 if str(s.get("registration_no", "")).startswith("21")]
    non_21_paid = [s for s in paid_142 if not str(s.get("registration_no", "")).startswith("21")]
    ordered_reg21_first = reg_21_paid + non_21_paid
    reg21_roll_lookup = {
        str(s["roll"]): str(START_BOARD_ROLL + i)
        for i, s in enumerate(ordered_reg21_first)
    }

    assigned_142 = []
    roll_map = {}

    for idx, st in enumerate(ordered_mar_first):
        c_roll = str(st["roll"]).strip()
        hsc_roll = str(START_BOARD_ROLL + idx)
        alt_seq_roll = seq_roll_lookup[c_roll]
        alt_reg21_roll = reg21_roll_lookup[c_roll]
        board_res = board_results.get(hsc_roll)

        e_list = ckpt.get(c_roll, {}).get("entries", [])
        ff_date = e_list[0].get("tx_date") if e_list else None
        ff_amount = e_list[0].get("amount") if e_list else None

        entry = dict(st)
        entry["hsc_roll"] = hsc_roll
        # Provide alternate roll candidates if they differ from hsc_roll
        if alt_seq_roll != hsc_roll:
            entry["hsc_roll_alt_by_payment_date"] = alt_seq_roll
        elif alt_reg21_roll != hsc_roll:
            entry["hsc_roll_alt_by_payment_date"] = alt_reg21_roll
        if alt_reg21_roll not in (hsc_roll, entry.get("hsc_roll_alt_by_payment_date")):
            entry["hsc_roll_alt_reg21"] = alt_reg21_roll

        entry["board_gpa_or_status"] = board_res
        entry["form_fillup_date"] = ff_date
        entry["form_fillup_amount"] = ff_amount
        entry["serial_no"] = idx + 1
        assigned_142.append(entry)

        roll_map[c_roll] = {
            "hsc_roll": hsc_roll,
            "hsc_roll_alt_by_payment_date": entry.get("hsc_roll_alt_by_payment_date"),
            "hsc_roll_alt_reg21": entry.get("hsc_roll_alt_reg21"),
            "registration_no": st.get("registration_no"),
            "name": st.get("name"),
            "board_gpa_or_status": board_res,
            "has_form_fill_up": True,
            "form_fillup_date": ff_date,
            "serial_no": idx + 1,
        }

    # Build 143 Year-2 file (142 paid + 1 unpaid Year-2 student 1202425030052)
    assigned_143 = list(assigned_142)
    assigned_149 = list(assigned_142)

    unpaid_year2 = [s for s in unpaid_7 if str(s.get("academic_year")) == "2"]
    unpaid_year1 = [s for s in unpaid_7 if str(s.get("academic_year")) != "2"]

    for st in unpaid_year2 + unpaid_year1:
        c_roll = str(st["roll"]).strip()
        entry = dict(st)
        entry["hsc_roll"] = None
        entry["candidate_tail_rolls"] = TAIL_BOARD_ROLLS
        entry["note"] = (
            "No Form fill-up receipt on college portal "
            "(if registered offline/late, tail board rolls 255021-255026 / 900134)"
        )
        entry["serial_no"] = len(assigned_149) + 1
        assigned_149.append(entry)
        if str(st.get("academic_year")) == "2":
            assigned_143.append(dict(entry, serial_no=len(assigned_143) + 1))

        roll_map[c_roll] = {
            "hsc_roll": None,
            "candidate_tail_rolls": TAIL_BOARD_ROLLS,
            "registration_no": st.get("registration_no"),
            "name": st.get("name"),
            "academic_year": st.get("academic_year"),
            "has_form_fill_up": False,
            "note": entry["note"],
            "serial_no": entry["serial_no"],
        }

    with open(OUTPUT_PAID_142_JSON, "w", encoding="utf-8") as f:
        json.dump(assigned_142, f, ensure_ascii=False, indent=2)

    with open(OUTPUT_YEAR2_143_JSON, "w", encoding="utf-8") as f:
        json.dump(assigned_143, f, ensure_ascii=False, indent=2)

    with open(OUTPUT_ALL_149_JSON, "w", encoding="utf-8") as f:
        json.dump(assigned_149, f, ensure_ascii=False, indent=2)

    with open(OUTPUT_ROLL_MAP_JSON, "w", encoding="utf-8") as f:
        json.dump(roll_map, f, ensure_ascii=False, indent=2)

    print(
        f"Total Form fill-up students assigned: {len(assigned_142)} "
        f"(HSC Rolls {START_BOARD_ROLL}..{START_BOARD_ROLL + len(assigned_142) - 1})"
    )
    print(f"Saved:\n  - {OUTPUT_PAID_142_JSON}\n  - {OUTPUT_YEAR2_143_JSON}\n  - {OUTPUT_ALL_149_JSON}\n  - {OUTPUT_ROLL_MAP_JSON}")


if __name__ == "__main__":
    main()
