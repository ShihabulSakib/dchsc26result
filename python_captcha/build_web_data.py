#!/usr/bin/env python3
"""
Generate clean, privacy-safe multi-group datasets for the static results web app.
Populates:
  - dist/data/manifest.json (and data/manifest.json)
  - dist/data/science.json (and data/science.json)
  - dist/data/humanities.json (and data/humanities.json)
  - dist/data/business_studies.json (and data/business_studies.json)
  - dist/students_data.json (combined with all students & subject marks)
  - dist/students.json (alias for students_data.json)
"""

import json
import re
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = ROOT.parent

# Science paths
SCIENCE_ASSIGNED_CANDIDATES = [
    ROOT / "assigned_hsc_rolls_862.json",
    PROJECT_ROOT / "hsc result science" / "assigned_hsc_rolls_862.json",
]
SCIENCE_PROGRESS_CANDIDATES = [
    ROOT / "results" / "marksheets_20261106_104600" / "progress.jsonl",
]

# Humanities paths
HUMANITIES_ASSIGNED_CANDIDATES = [
    PROJECT_ROOT / "hsc result humanities" / "assigned_hsc_rolls_humanities.json",
    ROOT / "assigned_hsc_rolls_humanities.json",
    PROJECT_ROOT / "hsc result humanities" / "assigned_hsc_rolls_149.json",
    PROJECT_ROOT / "hsc result humanities" / "assigned_hsc_rolls_143.json",
    PROJECT_ROOT / "hsc result humanities" / "assigned_hsc_rolls_142.json",
    PROJECT_ROOT / "hsc result humanities" / "humanities_all_students.json",
]
HUMANITIES_PROGRESS_CANDIDATES = [
    ROOT / "results" / "humanities_marksheets" / "progress.jsonl",
    ROOT / "results" / "humanities_marksheets" / "marksheets.json",
    PROJECT_ROOT / "hsc result humanities" / "progress.jsonl",
    PROJECT_ROOT / "hsc result humanities" / "marksheets.jsonl",
    PROJECT_ROOT / "hsc result humanities" / "marksheets.json",
]

# Business Studies paths
BUSINESS_ASSIGNED_CANDIDATES = [
    PROJECT_ROOT / "hsc result business studies" / "assigned_hsc_rolls_all_141.json",
    PROJECT_ROOT / "hsc result business studies" / "assigned_hsc_rolls_business.json",
    ROOT / "assigned_hsc_rolls_business.json",
    PROJECT_ROOT / "hsc result business studies" / "assigned_hsc_rolls_132.json",
    PROJECT_ROOT / "hsc result business studies" / "business_all_students.json",
]
BUSINESS_PROGRESS_CANDIDATES = [
    ROOT / "results" / "business_marksheets" / "progress.jsonl",
    ROOT / "results" / "business_marksheets" / "marksheets.json",
    PROJECT_ROOT / "hsc result business studies" / "progress.jsonl",
    PROJECT_ROOT / "hsc result business studies" / "marksheets.json",
]

OUTPUT_PATH = ROOT / "students_data.json"
OUTPUT_PATH_ALIAS = ROOT / "students.json"
DATA_DIR = ROOT / "data"
DIST_DIR = ROOT / "dist"
DIST_DATA_DIR = DIST_DIR / "data"

PCM_CODES = {"174-175", "176-177", "265-266"}
PCM_KEYWORDS = ("PHYSICS", "CHEMISTRY", "HIGHER MATHEMATICS", "MATHEMATICS")
COMPULSORY_CODES = {"101-102", "107-108", "275"}

SCIENCE_SECTION_RANGES = [
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


def first_existing(paths):
    for p in paths:
        if p.exists():
            return p
    return None


def discover_group_progress(roll_prefix, candidates):
    """Find explicit progress file or auto-discover from results/marksheets_* directories."""
    explicit = first_existing(candidates)
    if explicit:
        return explicit

    for base_results in (ROOT / "results", PROJECT_ROOT / "hsc result humanities" / "results", PROJECT_ROOT / "hsc result business studies" / "results"):
        if not base_results.exists():
            continue
        for sub in sorted(base_results.glob("marksheets_*"), reverse=True):
            for fname in ("progress.jsonl", "marksheets.json"):
                fpath = sub / fname
                if fpath.exists():
                    sample = fpath.read_text(encoding="utf-8", errors="ignore")[:4000]
                    if roll_prefix in sample:
                        return fpath
    return None


def get_section_from_roll(college_roll, group_key="science"):
    digits = re.sub(r"\D", "", str(college_roll or ""))
    roll_num = int(digits[-4:]) if len(digits) >= 4 else 0
    if group_key == "science":
        for sec, start, end, _label in SCIENCE_SECTION_RANGES:
            if start <= roll_num <= end:
                return sec
        return "Other"
    if 1 <= roll_num <= 200:
        return "A"
    elif 201 <= roll_num <= 400:
        return "B"
    return "A"


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
            code, grade, subj, marks_str = (
                m.group(1),
                m.group(2),
                clean_spaces(m.group(3)),
                m.group(4),
            )
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
            code, grade, subj = (
                m_no_marks.group(1),
                m_no_marks.group(2),
                clean_spaces(m_no_marks.group(3)),
            )
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


def parse_enrolled_profile_subjects(raw_subjects):
    """
    Convert either board subject objects ({code, subject, grade, marks})
    or Dhaka College profile subjects ({paper_1, paper_2, type}) into normalized items.
    """
    if not isinstance(raw_subjects, list):
        return []
    normalized = []
    for item in raw_subjects:
        if not isinstance(item, dict):
            continue
        if "code" in item and "subject" in item:
            code = str(item.get("code") or "")
            subj = clean_spaces(item.get("subject") or "")
            grade = str(item.get("grade") or "Pending")
            m_raw = item.get("marks")
            marks = int(m_raw) if str(m_raw or "").isdigit() else 0
            marks_display = (
                str(item.get("marks_display") or m_raw)
                if marks > 0
                else (str(item.get("marks_display") or "Pending"))
            )
            max_marks = int(item.get("max_marks") or (100 if code == "275" else 200))
            is_pcm = bool(
                item.get("is_pcm")
                or code in PCM_CODES
                or any(k in subj.upper() for k in PCM_KEYWORDS)
            )
            normalized.append({
                "code": code,
                "subject": subj,
                "subject_type": item.get("subject_type") or "",
                "grade": grade,
                "marks": marks,
                "marks_display": marks_display,
                "max_marks": max_marks,
                "is_pcm": is_pcm,
            })
            continue

        p1 = clean_spaces(item.get("paper_1") or "")
        p2 = clean_spaces(item.get("paper_2") or "")
        stype = clean_spaces(item.get("type") or "")

        m1 = re.match(r"^(\d+)\s*-\s*(.+)$", p1)
        m2 = re.match(r"^(\d+)\s*-\s*(.+)$", p2)

        code1 = m1.group(1) if m1 else ""
        name1 = m1.group(2) if m1 else p1
        code2 = m2.group(1) if m2 else ""

        code = f"{code1}-{code2}" if (code1 and code2) else (code1 or code2 or "—")
        subj_name = (
            re.sub(r"\s*[12](st|nd)\s*paper\s*$", "", name1, flags=re.IGNORECASE)
            .strip()
            .upper()
        )
        if code == "275" or subj_name == "ICT":
            subj_name = "INFORMATION & COMMUNICATION TECHNOLOGY"

        max_marks = 100 if code == "275" else 200
        is_pcm = code in PCM_CODES or any(k in subj_name for k in PCM_KEYWORDS)

        normalized.append({
            "code": code,
            "subject": subj_name,
            "subject_type": stype,
            "grade": "Pending",
            "marks": 0,
            "marks_display": "Pending",
            "max_marks": max_marks,
            "is_pcm": is_pcm,
        })
    return normalized


def load_progress_records(progress_path):
    """Load marksheet progress records from .jsonl, .json, or eduboard_fetch marksheets.json."""
    by_serial = {}
    by_roll = {}
    by_reg = {}
    if not progress_path or not progress_path.exists():
        return by_serial, by_roll, by_reg

    text = progress_path.read_text(encoding="utf-8").strip()
    if not text:
        return by_serial, by_roll, by_reg

    items = []
    if text.startswith("[") or text.startswith("{"):
        try:
            parsed = json.loads(text)
            if isinstance(parsed, list):
                items = parsed
            elif isinstance(parsed, dict) and isinstance(parsed.get("students"), list):
                items = parsed["students"]
        except json.JSONDecodeError:
            pass

    if not items:
        for line in text.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                items.append(json.loads(line))
            except json.JSONDecodeError:
                continue

    for item in items:
        if not isinstance(item, dict):
            continue
        src = item.get("source") or {}
        info = item.get("info") or {}

        # Index by college roll
        c_roll = (
            item.get("college_roll")
            or item.get("roll")
            or src.get("college_roll")
            or src.get("roll")
        )
        if c_roll:
            by_roll[str(c_roll).strip()] = item

        # Index by board roll
        hsc_roll = (
            item.get("hsc_roll")
            or item.get("roll_used")
            or info.get("rollNo")
        )
        if hsc_roll:
            by_roll[str(hsc_roll).strip()] = item

        # Index by registration number
        reg_no = (
            item.get("registration_no")
            or item.get("returned_reg")
            or info.get("regNo")
            or src.get("registration_no")
        )
        if reg_no:
            by_reg[str(reg_no).strip()] = item

        # Index by serial number
        serial = item.get("serial_no") or item.get("id") or src.get("id")
        if serial is not None:
            try:
                by_serial[int(serial)] = item
            except (ValueError, TypeError):
                pass

    return by_serial, by_roll, by_reg


def build_group_dataset(
    group_key,
    group_label,
    roll_prefix,
    assigned_path,
    progress_path,
    section_ranges,
):
    records_by_serial = {}
    records_by_roll = {}
    records_by_reg = {}

    assigned_list = []
    if assigned_path and assigned_path.exists():
        raw_assigned = json.loads(assigned_path.read_text(encoding="utf-8"))
        if isinstance(raw_assigned, dict) and "students" in raw_assigned:
            raw_assigned = raw_assigned["students"]
        if isinstance(raw_assigned, list):
            assigned_list = raw_assigned
            for idx, rec in enumerate(assigned_list, 1):
                if not isinstance(rec, dict):
                    continue
                serial = rec.get("serial_no") or rec.get("id") or idx
                try:
                    serial_int = int(serial)
                    records_by_serial[serial_int] = rec
                except (ValueError, TypeError):
                    pass
                r_str = str(rec.get("roll") or rec.get("college_roll") or "").strip()
                if r_str:
                    records_by_roll[r_str] = rec
                reg_str = str(rec.get("registration_no") or "").strip()
                if reg_str:
                    records_by_reg[reg_str] = rec

    progress_by_serial, progress_by_roll, progress_by_reg = load_progress_records(progress_path)

    # Determine all student records in natural order
    all_assigned = assigned_list
    if not all_assigned:
        all_serials = sorted(set(records_by_serial.keys()) | set(progress_by_serial.keys()))
        all_assigned = [records_by_serial.get(s, {}) for s in all_serials]

    students = []

    for idx, rec in enumerate(all_assigned, 1):
        serial = rec.get("serial_no") or rec.get("id") or idx
        try:
            serial_int = int(serial)
        except (ValueError, TypeError):
            serial_int = idx

        c_roll_candidate = str(
            rec.get("roll")
            or rec.get("college_roll")
            or f"{roll_prefix}{serial_int:04d}"
        ).strip()
        reg_candidate = str(rec.get("registration_no") or "").strip()
        hsc_candidate = str(rec.get("hsc_roll") or "").strip()

        prog = (
            (progress_by_reg.get(reg_candidate) if reg_candidate else None)
            or (progress_by_roll.get(c_roll_candidate) if c_roll_candidate else None)
            or (progress_by_roll.get(hsc_candidate) if hsc_candidate else None)
            or progress_by_serial.get(serial_int)
            or {}
        )

        info = prog.get("info") or {}
        src_obj = prog.get("source") or {}
        ident_obj = prog.get("identity") or {}
        ms_obj = prog.get("marksheet") or {}
        ver_obj = prog.get("verification") or {}

        status = (
            prog.get("status")
            or ver_obj.get("status")
            or ("pending" if not prog else "unknown")
        )
        raw_name = (
            info.get("name")
            or ident_obj.get("name_returned")
            or prog.get("returned_name")
            or prog.get("name")
            or src_obj.get("name")
            or rec.get("name")
            or f"Student #{serial_int}"
        )
        name = clean_spaces(raw_name)

        college_roll = str(
            rec.get("roll")
            or rec.get("college_roll")
            or prog.get("college_roll")
            or src_obj.get("college_roll")
            or f"{roll_prefix}{serial_int:04d}"
        ).strip()
        short_roll = college_roll[-4:] if len(college_roll) >= 4 else str(serial_int)
        section = get_section_from_roll(college_roll, group_key)

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
                    elif "code" in s and "subject" in s:
                        code = str(s.get("code") or "")
                        subj = clean_spaces(s.get("subject") or "")
                        grade = str(s.get("grade") or "")
                        m_raw = s.get("marks")
                        marks = int(m_raw) if str(m_raw or "").isdigit() else 0
                        marks_display = str(s.get("marks_display") or m_raw or marks)
                        max_marks = 100 if code == "275" else 200
                        is_pcm = code in PCM_CODES or any(k in subj.upper() for k in PCM_KEYWORDS)
                        subjects.append({
                            "code": code,
                            "subject": subj,
                            "grade": grade,
                            "marks": marks,
                            "marks_display": marks_display,
                            "max_marks": max_marks,
                            "is_pcm": is_pcm,
                        })
        if not subjects and isinstance(ms_obj.get("subjects"), list):
            subjects = parse_enrolled_profile_subjects(ms_obj["subjects"])
        if not subjects and isinstance(prog.get("subjects"), list):
            subjects = parse_enrolled_profile_subjects(prog["subjects"])
        if not subjects and isinstance(rec.get("subjects"), list):
            subjects = parse_enrolled_profile_subjects(rec["subjects"])

        total_marks = sum(s.get("marks", 0) for s in subjects)
        if not total_marks and isinstance(ms_obj.get("total_marks"), int):
            total_marks = ms_obj["total_marks"]

        overall_percentage = (
            round((total_marks / 1300.0) * 100.0, 2) if total_marks > 0 else 0.0
        )

        physics_marks = 0
        chemistry_marks = 0
        math_marks = 0
        compulsory_marks = 0

        for s in subjects:
            code = s.get("code", "")
            subj_upper = s.get("subject", "").upper()
            m_val = s.get("marks", 0)
            if code == "174-175" or "PHYSICS" in subj_upper:
                physics_marks = m_val
            elif code == "176-177" or "CHEMISTRY" in subj_upper:
                chemistry_marks = m_val
            elif code == "265-266" or "MATHEMATICS" in subj_upper:
                math_marks = m_val
            if code in COMPULSORY_CODES or any(
                w in subj_upper
                for w in ("BANGLA", "ENGLISH", "COMMUNICATION TECHNOLOGY", "ICT")
            ):
                compulsory_marks += m_val

        pcm_marks = physics_marks + chemistry_marks + math_marks
        pcm_percentile = round(pcm_marks / 6.0, 2) if pcm_marks > 0 else 0.0

        gpa_str = (
            info.get("gpa")
            or ms_obj.get("gpa")
            or prog.get("gpa")
            or (rec.get("board_gpa_or_status") if status != "ok" else None)
        )
        gpa_num = None
        if gpa_str is not None:
            try:
                gpa_num = round(float(gpa_str), 2)
            except (ValueError, TypeError):
                gpa_num = None

        result_flag = (
            info.get("result")
            or ms_obj.get("result")
            or ("P" if gpa_num else ("F" if status == "ok" else None))
        )

        students.append({
            "serial_no": serial_int,
            "college_roll": college_roll,
            "short_roll": short_roll,
            "section": section,
            "name": name,
            "group": group_label.upper(),
            "group_key": group_key,
            "session": clean_spaces(
                info.get("session")
                or ms_obj.get("session")
                or rec.get("session")
                or "2024-25"
            ),
            "academic_year": str(rec.get("academic_year") or "2"),
            "institute": clean_spaces(
                info.get("instituteName")
                or ms_obj.get("institute")
                or "DHAKA COLLEGE"
            ),
            "pass_year": info.get("passYear") or ident_obj.get("pass_year") or 2026,
            "status": status,
            "result": result_flag,
            "gpa": f"{gpa_num:.2f}"
            if gpa_num is not None
            else (str(gpa_str) if gpa_str else None),
            "gpa_value": gpa_num if gpa_num is not None else -1.0,
            "total_marks": total_marks,
            "max_total_marks": 1300,
            "overall_percentage": overall_percentage,
            "compulsory_marks": compulsory_marks,
            "pcm_marks": pcm_marks,
            "max_pcm_marks": 600,
            "pcm_percentile": pcm_percentile,
            "physics_marks": physics_marks,
            "chemistry_marks": chemistry_marks,
            "math_marks": math_marks,
            "subjects": subjects,
        })

    # Rank computation within group
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
        marks_rank_map[s["college_roll"]] = current_rank

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
        pcm_rank_map[s["college_roll"]] = current_pcm_rank

    for s in students:
        s["marks_rank"] = marks_rank_map.get(s["college_roll"])
        s["pcm_rank"] = pcm_rank_map.get(s["college_roll"])

    for sec, _start, _end, _label in section_ranges:
        sec_marks = [s for s in by_marks if s["section"] == sec]
        r_m = 0
        last_m = None
        for idx, s in enumerate(sec_marks, 1):
            if s["total_marks"] != last_m:
                r_m = idx
                last_m = s["total_marks"]
            s["section_marks_rank"] = r_m

        sec_pcm = [s for s in by_pcm if s["section"] == sec]
        r_p = 0
        last_p = None
        for idx, s in enumerate(sec_pcm, 1):
            if s["pcm_marks"] != last_p:
                r_p = idx
                last_p = s["pcm_marks"]
            s["section_pcm_rank"] = r_p

    ok_students = [s for s in students if s["total_marks"] > 0]
    gpa5_students = [s for s in students if s["gpa"] == "5.00"]
    min_roll = min((s["college_roll"] for s in students), default=f"{roll_prefix}0001")
    max_roll = max((s["college_roll"] for s in students), default=f"{roll_prefix}0150")

    return {
        "meta": {
            "title": f"Dhaka College HSC 2026 Results — {group_label}",
            "institute": "Dhaka College",
            "session": "2024-25",
            "exam": "HSC 2026",
            "group": group_label,
            "group_key": group_key,
            "roll_prefix": roll_prefix,
            "roll_range": f"{min_roll} – {max_roll}",
            "has_pcm": group_key == "science",
            "sections": [
                {"id": sec, "start": st, "end": en, "range": rng}
                for sec, st, en, rng in section_ranges
            ],
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "total_students": len(students),
            "with_marksheets": len(ok_students),
            "scraping_status": (
                "complete"
                if len(ok_students) > 0 and len(ok_students) >= len(students) * 0.9
                else ("in_progress" if len(students) > 0 else "pending")
            ),
            "gpa_5_count": len(gpa5_students),
            "highest_total": max((s["total_marks"] for s in ok_students), default=0),
            "highest_overall_percentage": max(
                (s["overall_percentage"] for s in ok_students), default=0.0
            ),
            "highest_pcm_percentile": max(
                (s["pcm_percentile"] for s in ok_students), default=0.0
            ),
        },
        "students": students,
    }


def build_all():
    DATA_DIR.mkdir(exist_ok=True)
    DIST_DIR.mkdir(exist_ok=True)
    DIST_DATA_DIR.mkdir(exist_ok=True)

    sci_assigned = first_existing(SCIENCE_ASSIGNED_CANDIDATES)
    sci_progress = discover_group_progress("120242501", SCIENCE_PROGRESS_CANDIDATES)
    science_payload = build_group_dataset(
        group_key="science",
        group_label="Science",
        roll_prefix="120242501",
        assigned_path=sci_assigned,
        progress_path=sci_progress,
        section_ranges=SCIENCE_SECTION_RANGES,
    )

    hum_assigned = first_existing(HUMANITIES_ASSIGNED_CANDIDATES)
    hum_progress = discover_group_progress("120242503", HUMANITIES_PROGRESS_CANDIDATES)
    humanities_sections = [
        ("A", 1, 160, "1202425030001 – 1202425030155"),
    ]
    humanities_payload = build_group_dataset(
        group_key="humanities",
        group_label="Humanities",
        roll_prefix="120242503",
        assigned_path=hum_assigned,
        progress_path=hum_progress,
        section_ranges=humanities_sections,
    )

    bus_assigned = first_existing(BUSINESS_ASSIGNED_CANDIDATES)
    bus_progress = discover_group_progress("120242502", BUSINESS_PROGRESS_CANDIDATES)
    business_sections = [
        ("A", 1, 160, "1202425020001 – 1202425020150"),
    ]
    business_payload = build_group_dataset(
        group_key="business_studies",
        group_label="Business Studies",
        roll_prefix="120242502",
        assigned_path=bus_assigned,
        progress_path=bus_progress,
        section_ranges=business_sections,
    )

    manifest = {
        "title": "Dhaka College HSC 2026 Result Portal",
        "institute": "Dhaka College",
        "session": "2024-25",
        "exam": "HSC 2026",
        "default_group": "science",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "groups": [
            {
                "key": "science",
                "label": "Science",
                "short_label": "Science",
                "data_url": "data/science.json",
                "roll_prefix": "120242501",
                "has_pcm": True,
                "total_students": science_payload["meta"]["total_students"],
                "with_marksheets": science_payload["meta"]["with_marksheets"],
                "gpa_5_count": science_payload["meta"]["gpa_5_count"],
                "scraping_status": science_payload["meta"]["scraping_status"],
            },
            {
                "key": "humanities",
                "label": "Humanities",
                "short_label": "Humanities",
                "data_url": "data/humanities.json",
                "roll_prefix": "120242503",
                "has_pcm": False,
                "total_students": humanities_payload["meta"]["total_students"],
                "with_marksheets": humanities_payload["meta"]["with_marksheets"],
                "gpa_5_count": humanities_payload["meta"]["gpa_5_count"],
                "scraping_status": humanities_payload["meta"]["scraping_status"],
            },
            {
                "key": "business_studies",
                "label": "Business Studies",
                "short_label": "Business",
                "data_url": "data/business_studies.json",
                "roll_prefix": "120242502",
                "has_pcm": False,
                "total_students": business_payload["meta"]["total_students"],
                "with_marksheets": business_payload["meta"]["with_marksheets"],
                "gpa_5_count": business_payload["meta"]["gpa_5_count"],
                "scraping_status": business_payload["meta"]["scraping_status"],
            },
        ],
    }

    # 1. Write individual lightweight group JSONs and manifest to both root/data and dist/data
    files_to_write = {
        "manifest.json": manifest,
        "science.json": science_payload,
        "humanities.json": humanities_payload,
        "business_studies.json": business_payload,
    }
    for fname, content in files_to_write.items():
        serialized = json.dumps(content, ensure_ascii=False, separators=(",", ":"))
        (DATA_DIR / fname).write_text(serialized, encoding="utf-8")
        (DIST_DATA_DIR / fname).write_text(serialized, encoding="utf-8")

    # 2. Combined students_data.json: contains ALL students from Science, Humanities, and Business Studies
    # with complete subject marks, without bloated redundant duplicate nested trees.
    all_students = (
        list(science_payload["students"])
        + list(humanities_payload["students"])
        + list(business_payload["students"])
    )

    combined_payload = {
        "meta": {
            "title": "Dhaka College HSC 2026 Results — All Cohorts",
            "institute": "Dhaka College",
            "session": "2024-25",
            "exam": "HSC 2026",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "total_students": len(all_students),
            "with_marksheets": sum(1 for s in all_students if s.get("total_marks", 0) > 0),
            "gpa_5_count": sum(1 for s in all_students if s.get("gpa") == "5.00"),
            "groups_summary": manifest["groups"],
        },
        "manifest": manifest,
        "students": all_students,
    }
    combined_serialized = json.dumps(
        combined_payload, ensure_ascii=False, separators=(",", ":")
    )
    OUTPUT_PATH.write_text(combined_serialized, encoding="utf-8")
    OUTPUT_PATH_ALIAS.write_text(combined_serialized, encoding="utf-8")
    (DIST_DIR / "students_data.json").write_text(combined_serialized, encoding="utf-8")
    (DIST_DIR / "students.json").write_text(combined_serialized, encoding="utf-8")

    # 3. Sync static web assets into dist/
    for asset in ("index.html", "styles.css", "app.js"):
        src = ROOT / asset
        if src.exists():
            (DIST_DIR / asset).write_bytes(src.read_bytes())

    print(
        f"Built multi-group web data & dist/data/:\n"
        f"  - Science:          {science_payload['meta']['total_students']} students ({science_payload['meta']['with_marksheets']} marksheets, GPA 5.00={science_payload['meta']['gpa_5_count']})\n"
        f"  - Humanities:       {humanities_payload['meta']['total_students']} students ({humanities_payload['meta']['with_marksheets']} marksheets, GPA 5.00={humanities_payload['meta']['gpa_5_count']}, status={humanities_payload['meta']['scraping_status']})\n"
        f"  - Business Studies: {business_payload['meta']['total_students']} students ({business_payload['meta']['with_marksheets']} marksheets, status={business_payload['meta']['scraping_status']})\n"
        f"  - Combined All:     {len(all_students)} total students written to students_data.json & students.json"
    )


if __name__ == "__main__":
    build_all()
