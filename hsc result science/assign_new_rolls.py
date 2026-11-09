import json
import os
import re
import subprocess

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(BASE_DIR)
DETAILED_INPUT_JSON = os.path.join(BASE_DIR, "receipt_extracted_details.json")
CHECKPOINT_FILE = os.path.join(BASE_DIR, "scrape_checkpoint.json")
BOARD_PDF = os.path.join(PROJECT_ROOT, "dhaka_hsc_2026_107977.pdf")
if not os.path.exists(BOARD_PDF):
    BOARD_PDF = os.path.join(BASE_DIR, "dhaka_hsc_2026_107977.pdf")

OUTPUT_PAID_853_JSON = os.path.join(BASE_DIR, "assigned_hsc_rolls_853.json")
OUTPUT_ALL_862_JSON = os.path.join(BASE_DIR, "assigned_hsc_rolls_862.json")
OUTPUT_ROLL_MAP_JSON = os.path.join(BASE_DIR, "college_to_hsc_roll_map.json")

START_BOARD_ROLL = 108727

ANCHORS = {
    "1202425010001": 108727,
    "1202425010466": 109176,
    "1202425010470": 109180,
    "1202425010471": 109181,
    "1202425010472": 109182,
    "1202425010778": 109471,
}


def load_board_results():
    if not os.path.exists(BOARD_PDF):
        return {}
    res = subprocess.run(
        ["pdftotext", "-layout", BOARD_PDF, "-"],
        capture_output=True,
        text=True,
        check=True
    )
    if ": SCIENCE :" not in res.stdout:
        return {}
    sci_text = res.stdout.split(": SCIENCE :")[1]
    entries = re.findall(r"(\d{6})\[([^\]]+)\]", sci_text)
    return {r: val.strip() for r, val in entries}


def main():
    with open(DETAILED_INPUT_JSON, "r", encoding="utf-8") as f:
        students = json.load(f)
    with open(CHECKPOINT_FILE, "r", encoding="utf-8") as f:
        ckpt = json.load(f)

    board_results = load_board_results()

    # Sort all 862 by college roll ascending
    students_sorted = sorted(students, key=lambda x: int(x["roll"]))

    # Separate the 853 who paid Form fill-up from the 9 Year-2 students who did not pay Form fill-up
    paid_853 = [s for s in students_sorted if s.get("has_form_fill_up")]
    unpaid_9 = [s for s in students_sorted if not s.get("has_form_fill_up")]

    # Primary block: 850 regular 21xxxxxxxx students who paid Form fill-up -> 108727..109576
    # Secondary block: 3 non-21xxxxxxxx Form fill-up students (1202425010030, 1202425010113, 1202425010895) -> 109577..109579
    reg_21_paid = [s for s in paid_853 if str(s.get("registration_no", "")).startswith("21")]
    non_21_paid = [s for s in paid_853 if not str(s.get("registration_no", "")).startswith("21")]

    ordered_paid_853 = reg_21_paid + non_21_paid

    # Also compute Model B (March 2026 on-time payers first, April/June late payers at end)
    mar_paid = [
        s for s in paid_853
        if "Mar-2026" in ckpt.get(str(s["roll"]), {}).get("entries", [{}])[0].get("tx_date", "")
    ]
    late_paid = [
        s for s in paid_853
        if "Mar-2026" not in ckpt.get(str(s["roll"]), {}).get("entries", [{}])[0].get("tx_date", "")
    ]
    ordered_mar_first = mar_paid + late_paid
    mar_roll_lookup = {
        str(s["roll"]): str(START_BOARD_ROLL + i)
        for i, s in enumerate(ordered_mar_first)
    }

    assigned_853 = []
    roll_map = {}

    for idx, st in enumerate(ordered_paid_853):
        c_roll = str(st["roll"]).strip()
        hsc_roll = str(START_BOARD_ROLL + idx)
        alt_hsc_roll = mar_roll_lookup[c_roll]
        board_res = board_results.get(hsc_roll)

        e_list = ckpt.get(c_roll, {}).get("entries", [])
        ff_date = e_list[0].get("tx_date") if e_list else None
        ff_amount = e_list[0].get("amount") if e_list else None

        entry = dict(st)
        entry["hsc_roll"] = hsc_roll
        if alt_hsc_roll != hsc_roll:
            entry["hsc_roll_alt_by_payment_date"] = alt_hsc_roll
        entry["board_gpa_or_status"] = board_res
        entry["form_fillup_date"] = ff_date
        entry["form_fillup_amount"] = ff_amount
        entry["serial_no"] = idx + 1
        assigned_853.append(entry)

        roll_map[c_roll] = {
            "hsc_roll": hsc_roll,
            "hsc_roll_alt_by_payment_date": alt_hsc_roll if alt_hsc_roll != hsc_roll else None,
            "registration_no": st.get("registration_no"),
            "name": st.get("name"),
            "board_gpa_or_status": board_res,
            "has_form_fill_up": True,
            "form_fillup_date": ff_date,
            "serial_no": idx + 1,
        }

    # Add the 9 unpaid Year-2 students at the end of the 862 file (marked has_form_fill_up=False)
    assigned_862 = list(assigned_853)
    for idx_u, st in enumerate(unpaid_9):
        c_roll = str(st["roll"]).strip()
        entry = dict(st)
        entry["hsc_roll"] = None
        entry["note"] = "No Form fill-up receipt on college portal (if registered offline/late, tail board rolls 109580-109586 / 900133)"
        entry["serial_no"] = len(assigned_853) + idx_u + 1
        assigned_862.append(entry)

        roll_map[c_roll] = {
            "hsc_roll": None,
            "registration_no": st.get("registration_no"),
            "name": st.get("name"),
            "has_form_fill_up": False,
            "note": entry["note"],
            "serial_no": entry["serial_no"],
        }

    print(f"Total Form fill-up students assigned: {len(assigned_853)} (HSC Rolls {START_BOARD_ROLL}..{START_BOARD_ROLL + len(assigned_853) - 1})")
    print("\nVerifying all 6 confirmed anchor points:")
    for c_roll, expected_b_roll in ANCHORS.items():
        actual_b_roll = int(roll_map[c_roll]["hsc_roll"])
        gpa = roll_map[c_roll]["board_gpa_or_status"]
        reg = roll_map[c_roll]["registration_no"]
        nm = roll_map[c_roll]["name"]
        assert actual_b_roll == expected_b_roll, f"Mismatch for {c_roll}: got {actual_b_roll}, expected {expected_b_roll}"
        print(f"  College Roll {c_roll} ({nm:28s}) -> HSC Roll: {actual_b_roll} | Reg: {reg} | Board GPA: {gpa} [MATCH]")

    with open(OUTPUT_PAID_853_JSON, "w", encoding="utf-8") as f:
        json.dump(assigned_853, f, ensure_ascii=False, indent=2)

    with open(OUTPUT_ALL_862_JSON, "w", encoding="utf-8") as f:
        json.dump(assigned_862, f, ensure_ascii=False, indent=2)

    with open(OUTPUT_ROLL_MAP_JSON, "w", encoding="utf-8") as f:
        json.dump(roll_map, f, ensure_ascii=False, indent=2)

    print(f"\nUpdated files:\n  - {OUTPUT_PAID_853_JSON}\n  - {OUTPUT_ALL_862_JSON}\n  - {OUTPUT_ROLL_MAP_JSON}")


if __name__ == "__main__":
    main()
