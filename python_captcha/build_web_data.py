#!/usr/bin/env python3
"""Generate clean, privacy-safe students_data.json for the static results web app."""

import json
import re
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
ASSIGNED_PATH = ROOT / "assigned_hsc_rolls_862.json"
PROGRESS_DIR = ROOT / "results" / "marksheets_20261106_104600"
PROGRESS_PATH = PROGRESS_DIR / "progress.jsonl"
OUTPUT_PATH = ROOT / "students_data.json"

PCM_CODES = {"174-175", "176-177", "265-266"}
PCM_KEYWORDS = ("PHYSICS", "CHEMISTRY", "HIGHER MATHEMATICS", "MATHEMATICS")

SECTION_RANGES = [
    ("A", 1, 150, "1202425010001 – 1202425010150"),
    ("B", 151, 300, "1202425010151 – 1202425010300"),
    ("C", 301, 450, "1202425010301 – 1202425010450"),
    ("D", 451, 600, "1202425010451 – 1202425010600"),
    ("E", 601, 750, "1202425010601 – 1202425010750"),
    ("F", 751, 900, "1202425010751 – 1202425010900"),
]


def clean_spaces(text):
    if not text:
        return ""
    return re.sub(r"\s+", " ", str(text)).strip()


def get_section_from_roll(college_roll):
    digits = re.sub(r"\D", "", str(college_roll or ""))
    roll_num = int(digits[-4:]) if len(digits) >= 4 else 0
    for sec, start, end, _label in SECTION_RANGES:
        if start <= roll_num <= end:
            return sec
    return "Other"


def parse_subject_string(raw_str):
    """Parse raw board subject string, including A- and F grades without trailing marks."""
    if not isinstance(raw_str, str) or not raw_str.strip():
        return []
    subjects = []
    for part in raw_str.split(","):
        part = part.strip()
        if not part:
            continue
        # Match: CODE GRADE SUBJECT MARKS (e.g. "101-102 A- BANGLA 137")
        m = re.match(r"^([\d-]+)\s+([A-Za-z+-]+)\s+(.*?)\s+(\d+)$", part)
        if m:
            code, grade, subj, marks_str = m.group(1), m.group(2), clean_spaces(m.group(3)), m.group(4)
            marks = int(marks_str)
            max_marks = 100 if code == "275" else 200
            is_pcm = code in PCM_CODES or any(k in subj.upper() for k in PCM_KEYWORDS)
            subjects.append({
                "code": code,
                "subject": subj,
                "grade": grade,
                "marks": marks,
                "marks_display": marks_str,
                "max_marks": max_marks,
                "is_pcm": is_pcm,
            })
            continue
        # Match without marks (e.g. "275 F INFORMATION & COMMUNICATION TECHNOLOGY")
        m_no_marks = re.match(r"^([\d-]+)\s+([A-Za-z+-]+)\s+(.*?)$", part)
        if m_no_marks:
            code, grade, subj = m_no_marks.group(1), m_no_marks.group(2), clean_spaces(m_no_marks.group(3))
            max_marks = 100 if code == "275" else 200
            is_pcm = code in PCM_CODES or any(k in subj.upper() for k in PCM_KEYWORDS)
            subjects.append({
                "code": code,
                "subject": subj,
                "grade": grade,
                "marks": 0,
                "marks_display": "—",
                "max_marks": max_marks,
                "is_pcm": is_pcm,
            })
    return subjects


def build_dataset():
    records_by_serial = {}
    if ASSIGNED_PATH.exists():
        raw_assigned = json.loads(ASSIGNED_PATH.read_text(encoding="utf-8"))
        for rec in raw_assigned:
            serial = rec.get("serial_no")
            if serial is not None:
                records_by_serial[int(serial)] = rec

    progress_by_serial = {}
    if PROGRESS_PATH.exists():
        for line in PROGRESS_PATH.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                item = json.loads(line)
            except json.JSONDecodeError:
                continue
            serial = item.get("serial_no")
            if serial is not None:
                progress_by_serial[int(serial)] = item

    all_serials = sorted(set(records_by_serial.keys()) | set(progress_by_serial.keys()))
    students = []

    for serial in all_serials:
        rec = records_by_serial.get(serial, {})
        prog = progress_by_serial.get(serial, {})
        info = prog.get("info") or {}

        status = prog.get("status") or ("pending" if not prog else "unknown")
        raw_name = info.get("name") or prog.get("returned_name") or rec.get("name") or f"Student #{serial}"
        name = clean_spaces(raw_name)

        college_roll = str(rec.get("roll") or f"120242501{serial:04d}").strip()
        short_roll = college_roll[-4:] if len(college_roll) >= 4 else str(serial)
        section = get_section_from_roll(college_roll)

        result_raw = prog.get("result_raw") or ""
        if not result_raw and isinstance(prog.get("raw"), dict):
            res_inner = prog["raw"].get("result")
            if isinstance(res_inner, dict):
                result_raw = res_inner.get("result") or ""

        subjects = parse_subject_string(result_raw)
        if not subjects and isinstance(prog.get("result"), list):
            for s in prog["result"]:
                if isinstance(s, dict):
                    if "raw" in s:
                        subjects.extend(parse_subject_string(s["raw"]))
                    else:
                        code = str(s.get("code") or "")
                        subj = clean_spaces(s.get("subject") or "")
                        grade = str(s.get("grade") or "")
                        marks_str = str(s.get("marks") or "")
                        marks = int(marks_str) if marks_str.isdigit() else 0
                        max_marks = 100 if code == "275" else 200
                        is_pcm = code in PCM_CODES or any(k in subj.upper() for k in PCM_KEYWORDS)
                        subjects.append({
                            "code": code,
                            "subject": subj,
                            "grade": grade,
                            "marks": marks,
                            "marks_display": marks_str if marks_str else "—",
                            "max_marks": max_marks,
                            "is_pcm": is_pcm,
                        })

        total_marks = sum(s["marks"] for s in subjects)
        physics_marks = 0
        chemistry_marks = 0
        math_marks = 0

        for s in subjects:
            code = s["code"]
            subj_upper = s["subject"].upper()
            if code == "174-175" or "PHYSICS" in subj_upper:
                physics_marks = s["marks"]
            elif code == "176-177" or "CHEMISTRY" in subj_upper:
                chemistry_marks = s["marks"]
            elif code == "265-266" or "MATHEMATICS" in subj_upper:
                math_marks = s["marks"]

        pcm_marks = physics_marks + chemistry_marks + math_marks
        # Formula: (Physics + Chemistry + Math) / 600 * 100 == (P + C + M) / 6
        pcm_percentile = round(pcm_marks / 6.0, 2) if subjects else 0.0

        gpa_str = info.get("gpa") or prog.get("gpa") or (rec.get("board_gpa_or_status") if status != "ok" else None)
        gpa_num = None
        if gpa_str is not None:
            try:
                gpa_num = round(float(gpa_str), 2)
            except (ValueError, TypeError):
                gpa_num = None

        result_flag = info.get("result") or ("P" if gpa_num else ("F" if status == "ok" else None))

        students.append({
            "serial_no": serial,
            "college_roll": college_roll,
            "short_roll": short_roll,
            "section": section,
            "name": name,
            "group": clean_spaces(info.get("groupName") or rec.get("student_group") or "SCIENCE").upper(),
            "session": clean_spaces(info.get("session") or rec.get("session") or "2024-25"),
            "institute": clean_spaces(info.get("instituteName") or "DHAKA COLLEGE"),
            "pass_year": info.get("passYear") or 2026,
            "status": status,
            "result": result_flag,
            "gpa": f"{gpa_num:.2f}" if gpa_num is not None else (str(gpa_str) if gpa_str else None),
            "gpa_value": gpa_num if gpa_num is not None else -1.0,
            "total_marks": total_marks,
            "max_total_marks": 1300,
            "pcm_marks": pcm_marks,
            "max_pcm_marks": 600,
            "pcm_percentile": pcm_percentile,
            "physics_marks": physics_marks,
            "chemistry_marks": chemistry_marks,
            "math_marks": math_marks,
            "subjects": subjects,
        })

    # Compute overall static ranks for Total Marks and PCM Percentile among students with marks
    by_marks = sorted(
        [s for s in students if s["total_marks"] > 0],
        key=lambda x: (x["total_marks"], x["pcm_marks"], x["gpa_value"]),
        reverse=True,
    )
    marks_rank_map = {}
    current_rank = 0
    last_score = None
    for idx, s in enumerate(by_marks, 1):
        if s["total_marks"] != last_score:
            current_rank = idx
            last_score = s["total_marks"]
        marks_rank_map[s["serial_no"]] = current_rank

    by_pcm = sorted(
        [s for s in students if s["pcm_marks"] > 0],
        key=lambda x: (x["pcm_marks"], x["total_marks"], x["gpa_value"]),
        reverse=True,
    )
    pcm_rank_map = {}
    current_pcm_rank = 0
    last_pcm = None
    for idx, s in enumerate(by_pcm, 1):
        if s["pcm_marks"] != last_pcm:
            current_pcm_rank = idx
            last_pcm = s["pcm_marks"]
        pcm_rank_map[s["serial_no"]] = current_pcm_rank

    for s in students:
        s["marks_rank"] = marks_rank_map.get(s["serial_no"])
        s["pcm_rank"] = pcm_rank_map.get(s["serial_no"])

    # Compute per-section ranks as well
    for sec, _start, _end, _label in SECTION_RANGES:
        sec_Marks = [s for s in by_marks if s["section"] == sec]
        r_m = 0
        last_m = None
        for idx, s in enumerate(sec_Marks, 1):
            if s["total_marks"] != last_m:
                r_m = idx
                last_m = s["total_marks"]
            s["section_marks_rank"] = r_m

        sec_Pcm = [s for s in by_pcm if s["section"] == sec]
        r_p = 0
        last_p = None
        for idx, s in enumerate(sec_Pcm, 1):
            if s["pcm_marks"] != last_p:
                r_p = idx
                last_p = s["pcm_marks"]
            s["section_pcm_rank"] = r_p

    ok_students = [s for s in students if s["total_marks"] > 0]
    payload = {
        "meta": {
            "title": "Dhaka College HSC 2026 Results",
            "institute": "Dhaka College",
            "session": "2024-25",
            "exam": "HSC 2026",
            "group": "Science",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "total_students": len(students),
            "with_marksheets": len(ok_students),
            "gpa_5_count": sum(1 for s in ok_students if s["gpa"] == "5.00"),
            "highest_total": max((s["total_marks"] for s in ok_students), default=0),
            "highest_pcm_percentile": max((s["pcm_percentile"] for s in ok_students), default=0.0),
        },
        "students": students,
    }

    OUTPUT_PATH.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")

    # Also populate a clean dist/ folder ready for static hosting (Netlify/Vercel/Cloudflare/GitHub Pages)
    dist_dir = ROOT / "dist"
    dist_dir.mkdir(exist_ok=True)
    for fname in ("index.html", "styles.css", "app.js", "students_data.json"):
        src = ROOT / fname
        if src.exists():
            (dist_dir / fname).write_bytes(src.read_bytes())

    print(
        f"Built {OUTPUT_PATH.name} & dist/: {len(students)} total students, "
        f"{len(ok_students)} with marksheets, "
        f"highest marks={payload['meta']['highest_total']}, "
        f"highest PCM={payload['meta']['highest_pcm_percentile']}%"
    )


if __name__ == "__main__":
    build_dataset()
