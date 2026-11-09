#!/usr/bin/env python3
import argparse
import base64
import csv
import json
import random
import re
import shutil
import sys
import time
from collections import Counter
from datetime import datetime
from difflib import SequenceMatcher
from pathlib import Path

import cv2
import numpy as np
import requests

import captcha_new

BASE = "https://eduboardresults.gov.bd"
CAPTCHA_URL = f"{BASE}/v1/captcha/generate-string-image-captcha"
RESULT_URL = f"{BASE}/api/rescrutiny/getStudentResult"

BOARD_NAMES = {
    10: "Dhaka",
    11: "Cumilla",
    12: "Chattogram",
    13: "Rajshahi",
    14: "Jashore",
    15: "Sylhet",
    16: "Barishal",
    17: "Dinajpur",
    18: "Mymensingh",
    19: "Madrasah",
    20: "Technical",
}

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "Origin": BASE,
    "Referer": f"{BASE}/",
}

RECOVERY_ROLL_OVERRIDES = {
    33: "109575",
    185: "900133",
    849: "109577",
    850: "109578",
    852: "108833",
    853: "109576",
}


def now_stamp():
    return datetime.now().isoformat(timespec="seconds")


def log(log_path, message, console=False):
    line = f"{now_stamp()} {message}"
    with open(log_path, "a", encoding="utf-8") as fh:
        fh.write(line + "\n")
    if console:
        print(line, flush=True)


def fmt_seconds(seconds):
    seconds = int(max(0, seconds))
    hours, rem = divmod(seconds, 3600)
    minutes, secs = divmod(rem, 60)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"


class Progress:
    def __init__(self, total, quiet=False):
        self.total = total
        self.quiet = quiet
        self.tty = sys.stdout.isatty()
        self.counts = Counter()
        self.last_len = 0

    def update(self, processed, item, avg_seconds):
        status = item.get("status") or "unknown"
        self.counts[status] += 1
        if self.quiet:
            return
        pct = (100.0 * processed / self.total) if self.total else 100.0
        eta = avg_seconds * max(0, self.total - processed)
        name = str(item.get("name") or "")[:24]
        line = (
            f"[{processed:>4}/{self.total}] {pct:5.1f}% | "
            f"ok:{self.counts.get('ok', 0)} nf:{self.counts.get('not_found', 0)} "
            f"fail:{self.counts.get('failed', 0)} rev:{self.counts.get('ambiguous', 0)} "
            f"ir:{self.counts.get('invalid_reg', 0)} "
            f"miss:{self.counts.get('missing_roll', 0)} | "
            f"{avg_seconds:4.1f}s/std | ETA {fmt_seconds(eta)} | "
            f"serial={item.get('serial_no')} {name} -> {status}"
        )
        if self.tty:
            width = shutil.get_terminal_size((140, 20)).columns
            line = line[: max(20, width - 1)]
            sys.stdout.write("\r" + line.ljust(self.last_len))
            sys.stdout.flush()
            self.last_len = len(line)
        else:
            print(line, flush=True)

    def notice(self, message):
        if self.quiet:
            return
        if self.tty:
            sys.stdout.write("\n")
            sys.stdout.flush()
            self.last_len = 0
        print(message, flush=True)

    def finish(self):
        if self.tty and not self.quiet:
            sys.stdout.write("\n")
            sys.stdout.flush()


def request_with_retries(session, method, url, *, retries, timeout, **kwargs):
    for attempt in range(retries + 1):
        try:
            resp = session.request(method, url, timeout=timeout, **kwargs)
        except requests.RequestException:
            if attempt >= retries:
                raise
            time.sleep(min(2 ** attempt, 30))
            continue
        if resp.status_code in (403, 429, 500, 502, 503, 504) and attempt < retries:
            retry_after = resp.headers.get("Retry-After", "")
            pause = int(retry_after) if retry_after.isdigit() else 2 ** attempt
            time.sleep(min(max(pause, 5), 120))
            continue
        return resp
    raise RuntimeError("request retry loop exhausted")


def make_session():
    session = requests.Session()
    session.headers.update(HEADERS)
    try:
        session.get(f"{BASE}/", timeout=20)
    except requests.RequestException:
        pass
    return session


def fetch_captcha(session, timeout, retries):
    resp = request_with_retries(
        session, "GET", CAPTCHA_URL, retries=retries, timeout=timeout
    )
    resp.raise_for_status()
    data = resp.json()
    raw = data.get("imageBase64") or data.get("image") or ""
    if isinstance(raw, str) and raw.startswith("data:"):
        raw = raw.split(",", 1)[1]
    img = cv2.imdecode(np.frombuffer(base64.b64decode(raw), np.uint8), cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError("could not decode captcha image")
    return img, data.get("hash"), data.get("timestamp")


def submit_result(session, text, captcha_hash, timestamp, roll, reg, board, year, timeout, retries):
    payload = {
        "rollNo": str(roll),
        "regNo": str(reg),
        "boardId": int(board),
        "passYear": int(year),
        "captchaText": text,
        "hash": captcha_hash,
        "timestamp": timestamp,
    }
    resp = request_with_retries(
        session,
        "POST",
        RESULT_URL,
        retries=retries,
        timeout=timeout,
        json=payload,
    )
    resp.raise_for_status()
    return resp.json(), payload


def classify(resp):
    if not isinstance(resp, dict):
        return "error"
    msg = str(resp.get("message") or resp.get("msg") or "").strip().lower()
    if "invalid captcha" in msg:
        return "invalid_captcha"
    if any(
        token in msg
        for token in ("invalid reg", "invalid registration", "invalid roll")
    ):
        return "invalid_reg"
    if "not found" in msg or "no result" in msg:
        return "not_found"
    if resp.get("info") or resp.get("result") or resp.get("results"):
        return "ok"
    status = resp.get("status")
    if status in (200, 201, "200", "201", True) and msg in ("", "success", "ok"):
        return "ok"
    return "error"


def pick(mapping, *keys):
    if not isinstance(mapping, dict):
        return None
    for key in keys:
        value = mapping.get(key)
        if value not in (None, "", [], {}):
            return value
    return None


def parse_subjects(raw):
    if not isinstance(raw, str):
        return raw if isinstance(raw, list) else []
    subjects = []
    for part in raw.split(","):
        part = part.strip()
        if not part:
            continue
        match = re.match(r"^([\d-]+)\s+([A-Za-z+-]+)\s+(.*?)\s+(\d+)$", part)
        if match:
            subjects.append(
                {
                    "code": match.group(1),
                    "grade": match.group(2),
                    "subject": match.group(3).strip(),
                    "marks": match.group(4),
                }
            )
            continue
        match = re.match(r"^([\d-]+)\s+([A-Za-z+-]+)\s+(.*?)$", part)
        if match:
            subjects.append(
                {
                    "code": match.group(1),
                    "grade": match.group(2),
                    "subject": match.group(3).strip(),
                    "marks": None,
                }
            )
        else:
            subjects.append({"raw": part})
    return subjects


def extract_fields(resp):
    result_obj = resp.get("result")
    info = {}
    result_raw = None
    subjects = []
    if isinstance(result_obj, dict):
        info = result_obj.get("info") or {}
        result_raw = result_obj.get("result")
        subjects = parse_subjects(result_raw)
        if not subjects:
            subjects = result_obj.get("subjects") or []
    elif isinstance(result_obj, list):
        subjects = result_obj
    if not info:
        info = resp.get("info") or resp.get("student") or resp.get("studentInfo") or {}
    if not isinstance(info, dict):
        info = {}
    return {
        "info": info,
        "result": subjects,
        "result_raw": result_raw,
        "name": pick(info, "name", "studentName", "student_name", "fullName"),
        "reg": pick(info, "regNo", "registrationNo", "registration_no", "reg"),
        "roll": pick(info, "rollNo", "roll_no", "roll", "hscRoll"),
        "gpa": pick(info, "gpa", "GPA", "cgpa") or pick(resp, "gpa", "GPA"),
    }


def norm_name(value):
    return re.sub(r"[^A-Z0-9]+", " ", str(value or "").upper()).strip()


def name_similarity(left, right):
    a, b = norm_name(left), norm_name(right)
    if not a or not b:
        return None
    if a == b:
        return 1.0
    return SequenceMatcher(None, a, b).ratio()


def names_match(left, right):
    sim = name_similarity(left, right)
    return None if sim is None else sim >= 0.88


def normalize_digits(value):
    return re.sub(r"\D", "", str(value or ""))


def numeric(value):
    try:
        return float(str(value).strip())
    except (TypeError, ValueError):
        return None


def gpa_matches(expected, returned):
    a, b = numeric(expected), numeric(returned)
    if a is None or b is None:
        return None
    return abs(a - b) < 0.005


def record_rolls(rec):
    rolls = []

    def add(value):
        value = str(value or "").strip()
        if value and value not in rolls:
            rolls.append(value)

    serial = rec.get("serial_no")
    group = str(rec.get("student_group") or "").strip().lower()
    if group == "science":
        add(RECOVERY_ROLL_OVERRIDES.get(serial) or RECOVERY_ROLL_OVERRIDES.get(str(serial)))
    primary = str(rec.get("hsc_roll") or "").strip()
    alt = rec.get("hsc_roll_alt_by_payment_date")
    alt_reg21 = rec.get("hsc_roll_alt_reg21")
    add(primary)
    if primary.isdigit():
        width = len(primary)
        add(str(int(primary) + 1).zfill(width))
    add(alt)
    if primary.isdigit():
        width = len(primary)
        add(str(int(primary) - 1).zfill(width))
    if alt and str(alt).isdigit():
        width = len(str(alt))
        add(str(int(alt) - 1).zfill(width))
        add(str(int(alt) + 1).zfill(width))
    add(alt_reg21)
    for tail_roll in rec.get("candidate_tail_rolls") or []:
        add(tail_roll)
    return rolls


def try_text(session, args, text, captcha_hash, timestamp, rolls, rec):
    attempts = 0
    outcomes = []
    for roll in rolls:
        resp, _ = submit_result(
            session,
            text,
            captcha_hash,
            timestamp,
            roll,
            rec["registration_no"],
            args.board,
            args.year,
            args.timeout,
            args.http_retries,
        )
        attempts += 1
        kind = classify(resp)
        if kind == "invalid_captcha":
            return "invalid", attempts, None, outcomes, "invalid captcha"
        if kind == "invalid_reg":
            outcomes.append((roll, "invalid_reg", resp))
            continue
        if kind == "not_found":
            outcomes.append((roll, "not_found", resp))
            continue
        if kind == "ok":
            fields = extract_fields(resp)
            reg_ok = None
            if fields["reg"]:
                reg_ok = normalize_digits(fields["reg"]) == normalize_digits(rec["registration_no"])
            name_ok = names_match(rec.get("name"), fields["name"])
            if reg_ok is False:
                outcomes.append((roll, "reg_mismatch", resp))
                continue
            if reg_ok is None and name_ok is False:
                outcomes.append((roll, "name_mismatch", resp))
                continue
            success = {
                "roll_used": roll,
                "response": resp,
                "fields": fields,
                "reg_ok": reg_ok,
                "name_ok": name_ok,
            }
            return "ok", attempts, success, outcomes, None
        status = resp.get("status") if isinstance(resp, dict) else None
        outcomes.append((roll, f"api_error:{status}", resp))

    kinds = [item[1] for item in outcomes]
    if any(kind in ("reg_mismatch", "name_mismatch") for kind in kinds):
        return "ambiguous", attempts, None, outcomes, "roll/registration mismatch"
    if any(kind == "invalid_reg" for kind in kinds):
        return "invalid_reg", attempts, None, outcomes, "invalid registration/roll"
    if any(kind == "not_found" for kind in kinds):
        return "not_found", attempts, None, outcomes, "result not found"
    return "error", attempts, None, outcomes, "API error"


def lookup(session, args, rec, debug_dir):
    start = time.time()
    serial = rec.get("serial_no")
    rolls = record_rolls(rec)
    base = {
        "serial_no": serial,
        "id": rec.get("id"),
        "name": rec.get("name"),
        "registration_no": rec.get("registration_no"),
        "hsc_roll": rec.get("hsc_roll"),
        "hsc_roll_alt": rec.get("hsc_roll_alt_by_payment_date"),
        "expected_gpa": rec.get("board_gpa_or_status"),
        "student_group": rec.get("student_group"),
        "session": rec.get("session"),
        "roll_used": None,
        "status": None,
        "returned_name": None,
        "returned_reg": None,
        "gpa": None,
        "subjects_count": 0,
        "info": None,
        "result": None,
        "result_raw": None,
        "raw": None,
        "error": None,
        "attempts": 0,
        "captcha_attempts": 0,
        "captcha_text": None,
        "duration_s": None,
    }
    if not rolls:
        base["status"] = "missing_roll"
        base["duration_s"] = round(time.time() - start, 2)
        return base

    last_img = None
    last_error = None
    last_outcomes = []
    for refresh in range(args.max_captcha_refreshes):
        try:
            img, captcha_hash, timestamp = fetch_captcha(
                session, args.timeout, args.http_retries
            )
        except Exception as exc:
            last_error = f"captcha fetch: {exc}"
            time.sleep(min(30, 2 ** refresh))
            continue
        last_img = img
        base["captcha_attempts"] += 1
        use_fast = (not args.no_fast) and refresh < args.fast_refreshes
        best, candidates = captcha_new.solve_candidates(
            img,
            length=6,
            max_workers=args.captcha_workers,
            limit=args.max_candidates,
            fast=use_fast,
        )
        if best not in candidates:
            candidates = [best] + candidates
        for text in candidates[: args.max_candidates]:
            outcome, attempts, success, outcomes, error = try_text(
                session, args, text, captcha_hash, timestamp, rolls, rec
            )
            base["attempts"] += attempts
            base["captcha_text"] = text
            last_error = error
            last_outcomes = outcomes
            if outcome == "invalid":
                continue
            if outcome == "ok":
                fields = success["fields"]
                base.update(
                    {
                        "roll_used": success["roll_used"],
                        "status": "ok",
                        "returned_name": fields["name"],
                        "returned_reg": fields["reg"],
                        "gpa": fields["gpa"],
                        "subjects_count": len(fields["result"]) if isinstance(fields["result"], list) else 0,
                        "info": fields["info"],
                        "result": fields["result"],
                        "result_raw": fields["result_raw"],
                        "raw": success["response"],
                        "error": None,
                    }
                )
                base["duration_s"] = round(time.time() - start, 2)
                return base
            if outcome == "not_found":
                base["status"] = "not_found"
                base["error"] = error
                base["raw"] = [item[2] for item in outcomes]
                base["duration_s"] = round(time.time() - start, 2)
                return base
            if outcome == "invalid_reg":
                base["status"] = "invalid_reg"
                base["error"] = error
                base["raw"] = [item[2] for item in outcomes]
                base["duration_s"] = round(time.time() - start, 2)
                return base
            if outcome == "ambiguous":
                base["status"] = "ambiguous"
                base["error"] = error
                base["raw"] = [item[2] for item in outcomes]
                base["duration_s"] = round(time.time() - start, 2)
                return base
            break

    base["status"] = "failed"
    base["error"] = last_error
    if last_outcomes:
        base["raw"] = [item[2] for item in last_outcomes]
    base["duration_s"] = round(time.time() - start, 2)
    if args.debug_captcha and last_img is not None:
        debug_dir.mkdir(parents=True, exist_ok=True)
        cv2.imwrite(str(debug_dir / f"serial_{serial}.png"), last_img)
    return base


def load_records(path):
    with open(path, encoding="utf-8") as fh:
        data = json.load(fh)
    if isinstance(data, dict):
        data = data.get("students") or data.get("data") or []
    return data


def build_marksheet(rec, item, args):
    info = item.get("info") or {}
    raw_result = item.get("result_raw")
    if isinstance(raw_result, str) and raw_result.strip():
        subjects = parse_subjects(raw_result)
    else:
        subjects = item.get("result") or []
    status = item.get("status") or "unknown"

    name_expected = rec.get("name")
    name_returned = item.get("returned_name") or info.get("name")
    reg_expected = rec.get("registration_no")
    reg_returned = item.get("returned_reg") or info.get("regNo")
    roll_expected = rec.get("hsc_roll")
    roll_alt = rec.get("hsc_roll_alt_by_payment_date")
    roll_used = item.get("roll_used") or info.get("rollNo")
    expected_gpa = rec.get("board_gpa_or_status")
    returned_gpa = item.get("gpa") or info.get("gpa")

    name_ok = names_match(name_expected, name_returned)
    name_sim = name_similarity(name_expected, name_returned)
    reg_ok = None
    if reg_expected and reg_returned:
        reg_ok = normalize_digits(reg_expected) == normalize_digits(reg_returned)
    gpa_ok = gpa_matches(expected_gpa, returned_gpa)

    flags = []
    if status == "invalid_reg":
        flags.append("invalid_reg")
    if status == "ok":
        if name_ok is False:
            flags.append("name_mismatch")
        if reg_ok is False:
            flags.append("reg_mismatch")
        if gpa_ok is False:
            flags.append("gpa_mismatch")
        if name_ok is None:
            flags.append("name_missing")
        if reg_ok is None:
            flags.append("reg_missing")
        if gpa_ok is None:
            flags.append("gpa_unavailable")

    verified = bool(name_ok is True and reg_ok is True)
    subject_count = len(subjects) if isinstance(subjects, list) else 0
    total_marks = 0
    for subject in subjects if isinstance(subjects, list) else []:
        marks = subject.get("marks") if isinstance(subject, dict) else None
        if marks and str(marks).isdigit():
            total_marks += int(marks)

    marksheet = None
    if status == "ok":
        marksheet = {
            "institute": info.get("instituteName"),
            "eiin": info.get("eiin"),
            "group": info.get("groupName"),
            "session": info.get("session"),
            "result": info.get("result"),
            "gpa": returned_gpa,
            "gpa_expected": expected_gpa,
            "gpa_match": gpa_ok,
            "subject_count": subject_count,
            "total_marks": total_marks,
            "subjects": subjects,
        }

    return {
        "serial_no": rec.get("serial_no"),
        "source": {
            "id": rec.get("id"),
            "name": rec.get("name"),
            "college_roll": rec.get("roll"),
            "admission_roll": rec.get("admission_roll"),
            "father_name": rec.get("father_name"),
            "mother_name": rec.get("mother_name"),
            "group": rec.get("student_group"),
            "session": rec.get("session"),
        },
        "identity": {
            "name_expected": name_expected,
            "name_returned": name_returned,
            "hsc_roll_primary": roll_expected,
            "hsc_roll_alt": roll_alt,
            "roll_used": roll_used,
            "returned_roll": info.get("rollNo"),
            "registration_no": reg_expected,
            "returned_reg": reg_returned,
            "board": BOARD_NAMES.get(args.board, str(args.board)),
            "board_id": args.board,
            "pass_year": args.year,
            "exam_type": "HSC",
        },
        "marksheet": marksheet,
        "verification": {
            "status": status,
            "verified": verified,
            "name_match": name_ok,
            "name_similarity": round(name_sim, 3) if name_sim is not None else None,
            "reg_match": reg_ok,
            "gpa_match": gpa_ok,
            "flags": flags,
        },
        "fetch": {
            "captcha_attempts": item.get("captcha_attempts"),
            "api_attempts": item.get("attempts"),
            "duration_s": item.get("duration_s"),
            "fetched_at": item.get("fetched_at"),
            "error": item.get("error"),
            "raw": item.get("raw") if status != "ok" else None,
        },
    }


def write_marksheets(out_dir, done, records_all, args, elapsed_s):
    marksheets = []
    for rec in records_all:
        serial = rec.get("serial_no")
        item = done.get(serial)
        if item is not None:
            marksheets.append(build_marksheet(rec, item, args))
    marksheets.sort(key=lambda item: (item.get("serial_no") is None, item.get("serial_no")))

    with open(out_dir / "marksheets.json", "w", encoding="utf-8") as fh:
        json.dump(marksheets, fh, ensure_ascii=False, indent=2)

    fields = [
        "serial_no",
        "id",
        "name",
        "name_returned",
        "college_roll",
        "hsc_roll_primary",
        "hsc_roll_alt",
        "roll_used",
        "registration_no",
        "returned_reg",
        "board",
        "pass_year",
        "group",
        "session",
        "institute",
        "result",
        "gpa",
        "gpa_expected",
        "gpa_match",
        "name_match",
        "name_similarity",
        "reg_match",
        "verified",
        "flags",
        "subject_count",
        "total_marks",
        "captcha_attempts",
        "api_attempts",
        "duration_s",
        "status",
    ]
    with open(out_dir / "marksheets.csv", "w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        for item in marksheets:
            source = item["source"]
            identity = item["identity"]
            marksheet = item["marksheet"] or {}
            verification = item["verification"]
            fetch = item["fetch"]
            writer.writerow(
                {
                    "serial_no": item["serial_no"],
                    "id": source.get("id"),
                    "name": source.get("name"),
                    "name_returned": identity.get("name_returned"),
                    "college_roll": source.get("college_roll"),
                    "hsc_roll_primary": identity.get("hsc_roll_primary"),
                    "hsc_roll_alt": identity.get("hsc_roll_alt"),
                    "roll_used": identity.get("roll_used"),
                    "registration_no": identity.get("registration_no"),
                    "returned_reg": identity.get("returned_reg"),
                    "board": identity.get("board"),
                    "pass_year": identity.get("pass_year"),
                    "group": marksheet.get("group") or source.get("group"),
                    "session": marksheet.get("session") or source.get("session"),
                    "institute": marksheet.get("institute"),
                    "result": marksheet.get("result"),
                    "gpa": marksheet.get("gpa"),
                    "gpa_expected": marksheet.get("gpa_expected"),
                    "gpa_match": verification.get("gpa_match"),
                    "name_match": verification.get("name_match"),
                    "name_similarity": verification.get("name_similarity"),
                    "reg_match": verification.get("reg_match"),
                    "verified": verification.get("verified"),
                    "flags": ";".join(verification.get("flags") or []),
                    "subject_count": marksheet.get("subject_count", 0),
                    "total_marks": marksheet.get("total_marks", 0),
                    "captcha_attempts": fetch.get("captcha_attempts"),
                    "api_attempts": fetch.get("api_attempts"),
                    "duration_s": fetch.get("duration_s"),
                    "status": verification.get("status"),
                }
            )

    failures = [
        item
        for item in marksheets
        if item["verification"]["status"] != "missing_roll"
        and (
            item["verification"]["status"]
            in ("failed", "error", "ambiguous", "not_found", "invalid_reg")
            or item["verification"]["verified"] is False
        )
    ]
    missing = [item for item in marksheets if item["verification"]["status"] == "missing_roll"]

    with open(out_dir / "failures.json", "w", encoding="utf-8") as fh:
        json.dump(failures, fh, ensure_ascii=False, indent=2)
    with open(out_dir / "missing_rolls.json", "w", encoding="utf-8") as fh:
        json.dump(missing, fh, ensure_ascii=False, indent=2)

    counts = Counter(item["verification"]["status"] for item in marksheets)
    flag_counts = Counter(
        flag for item in marksheets for flag in item["verification"]["flags"]
    )
    summary = {
        "generated_at": now_stamp(),
        "elapsed_s": round(elapsed_s, 1),
        "elapsed": fmt_seconds(elapsed_s),
        "total": len(marksheets),
        "counts": dict(counts),
        "verified": sum(1 for item in marksheets if item["verification"]["verified"]),
        "flags": dict(flag_counts),
        "output": str(out_dir),
    }
    with open(out_dir / "summary.json", "w", encoding="utf-8") as fh:
        json.dump(summary, fh, ensure_ascii=False, indent=2)

    if args.serials:
        tests = []
        for item in marksheets:
            identity = item["identity"]
            marksheet = item["marksheet"] or {}
            verification = item["verification"]
            tests.append(
                {
                    "serial_no": item["serial_no"],
                    "expected_name": identity.get("name_expected"),
                    "returned_name": identity.get("name_returned"),
                    "name_match": verification.get("name_match"),
                    "name_similarity": verification.get("name_similarity"),
                    "expected_reg": identity.get("registration_no"),
                    "returned_reg": identity.get("returned_reg"),
                    "reg_match": verification.get("reg_match"),
                    "expected_gpa": marksheet.get("gpa_expected"),
                    "returned_gpa": marksheet.get("gpa"),
                    "gpa_match": verification.get("gpa_match"),
                    "roll_used": identity.get("roll_used"),
                    "subject_count": marksheet.get("subject_count", 0),
                    "total_marks": marksheet.get("total_marks", 0),
                    "status": verification.get("status"),
                    "flags": verification.get("flags"),
                }
            )
        with open(out_dir / "test_summary.json", "w", encoding="utf-8") as fh:
            json.dump(tests, fh, ensure_ascii=False, indent=2)

    return summary


def main():
    parser = argparse.ArgumentParser(
        description="Fetch HSC results and write organized marksheets."
    )
    parser.add_argument("--input", default="assigned_hsc_rolls_862.json")
    parser.add_argument("--out", default=None, help="output directory")
    parser.add_argument("--serials", default="", help="comma-separated serial numbers")
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--board", type=int, default=10)
    parser.add_argument("--year", type=int, default=2026)
    parser.add_argument("--timeout", type=float, default=25)
    parser.add_argument("--http-retries", type=int, default=3)
    parser.add_argument("--max-captcha-refreshes", type=int, default=6)
    parser.add_argument("--max-candidates", type=int, default=8)
    parser.add_argument("--captcha-workers", type=int, default=3)
    parser.add_argument("--no-fast", action="store_true", help="always use the full captcha pipeline")
    parser.add_argument("--fast-refreshes", type=int, default=2, help="fast attempts before full solver")
    parser.add_argument("--min-delay", type=float, default=1.0)
    parser.add_argument("--max-delay", type=float, default=2.0)
    parser.add_argument("--pause-every", type=int, default=100)
    parser.add_argument("--pause-seconds", type=float, default=20)
    parser.add_argument("--target-minutes", type=float, default=85)
    parser.add_argument("--max-runtime-minutes", type=float, default=90)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--retry-failures", action="store_true")
    parser.add_argument("--debug-captcha", action="store_true")
    parser.add_argument("--print-raw", action="store_true")
    parser.add_argument("--no-progress", action="store_true")
    args = parser.parse_args()

    if args.target_minutes > args.max_runtime_minutes:
        args.target_minutes = args.max_runtime_minutes

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_dir = Path(args.out) if args.out else Path("results") / f"marksheets_{stamp}"
    out_dir.mkdir(parents=True, exist_ok=True)
    debug_dir = out_dir / "debug"
    log_path = out_dir / "run.log"
    progress_path = out_dir / "progress.jsonl"

    records_all = load_records(args.input)
    records = records_all
    if args.serials:
        wanted = {int(item) for item in args.serials.split(",") if item.strip()}
        records = [rec for rec in records if int(rec.get("serial_no", -1)) in wanted]
    if args.limit:
        records = records[: args.limit]

    done = {}
    if args.resume and progress_path.exists():
        for line in progress_path.read_text(encoding="utf-8").splitlines():
            try:
                item = json.loads(line)
                done[item.get("serial_no")] = item
            except json.JSONDecodeError:
                continue
    elif progress_path.exists():
        progress_path.write_text("", encoding="utf-8")

    pending = []
    for rec in records:
        serial = rec.get("serial_no")
        previous = done.get(serial)
        if previous and args.resume:
            if previous.get("status") in ("ok", "not_found", "missing_roll"):
                continue
            if not args.retry_failures:
                continue
        pending.append(rec)

    session = make_session()
    log(
        log_path,
        f"start records={len(records)} pending={len(pending)} out={out_dir} "
        f"board={args.board} year={args.year}",
        console=True,
    )
    if not pending:
        log(log_path, "nothing to do", console=True)

    progress = Progress(len(pending), quiet=args.no_progress)
    run_start = time.monotonic()
    target_deadline = run_start + args.target_minutes * 60
    hard_deadline = run_start + args.max_runtime_minutes * 60
    stopped_early = False
    pacing_reduced = False

    with open(progress_path, "a", encoding="utf-8") as jsonl:
        for index, rec in enumerate(pending, 1):
            if time.monotonic() >= hard_deadline:
                stopped_early = True
                break
            serial = rec.get("serial_no")
            try:
                item = lookup(session, args, rec, debug_dir)
            except Exception as exc:
                item = {
                    "serial_no": serial,
                    "id": rec.get("id"),
                    "name": rec.get("name"),
                    "registration_no": rec.get("registration_no"),
                    "hsc_roll": rec.get("hsc_roll"),
                    "hsc_roll_alt": rec.get("hsc_roll_alt_by_payment_date"),
                    "expected_gpa": rec.get("board_gpa_or_status"),
                    "student_group": rec.get("student_group"),
                    "session": rec.get("session"),
                    "roll_used": None,
                    "status": "failed",
                    "returned_name": None,
                    "returned_reg": None,
                    "gpa": None,
                    "subjects_count": 0,
                    "info": None,
                    "result": None,
                    "result_raw": None,
                    "raw": None,
                    "error": f"{type(exc).__name__}: {exc}",
                    "attempts": 0,
                    "captcha_attempts": 0,
                    "captcha_text": None,
                    "duration_s": None,
                }
            item["fetched_at"] = now_stamp()
            done[serial] = item
            jsonl.write(json.dumps(item, ensure_ascii=False) + "\n")
            jsonl.flush()

            elapsed = time.monotonic() - run_start
            avg = elapsed / index
            progress.update(index, item, avg)
            log(
                log_path,
                f"[{index}/{len(pending)}] serial={serial} status={item.get('status')} "
                f"roll_used={item.get('roll_used')} returned={item.get('returned_name')} "
                f"gpa={item.get('gpa')} attempts={item.get('attempts')} "
                f"error={item.get('error')}",
                console=args.no_progress,
            )
            if args.print_raw and item.get("raw"):
                log(
                    log_path,
                    f"raw serial={serial}: {json.dumps(item['raw'], ensure_ascii=False)[:2000]}",
                )

            remaining = len(pending) - index
            if remaining <= 0:
                break

            remaining_budget = target_deadline - time.monotonic()
            projected = avg * remaining
            min_delay, max_delay = args.min_delay, args.max_delay
            if projected > max(remaining_budget, 1) * 0.92:
                min_delay, max_delay = 0.2, 0.6
                if not pacing_reduced:
                    progress.notice("Pacing reduced to keep the run under the target time.")
                    log(log_path, "pacing reduced", console=False)
                    pacing_reduced = True

            if args.pause_every and index % args.pause_every == 0:
                pause = args.pause_seconds
                if projected + pause > remaining_budget:
                    pause = 0
                if pause:
                    progress.notice(
                        f"Cool-down: sleeping {pause:.0f}s after {index} students."
                    )
                    log(log_path, f"cool-down {pause:.0f}s", console=False)
                    time.sleep(pause)

            delay = random.uniform(min_delay, max_delay)
            if time.monotonic() + delay >= hard_deadline:
                stopped_early = True
                break
            time.sleep(delay)

    progress.finish()
    elapsed = time.monotonic() - run_start
    summary = write_marksheets(out_dir, done, records_all, args, elapsed)
    processed_this_run = sum(progress.counts.values())

    print("=" * 64)
    print(" RUN COMPLETE" if not stopped_early else " RUN STOPPED AT TIME CAP")
    print("=" * 64)
    print(f" Processed this run : {processed_this_run}")
    print(f" Total marksheets   : {summary['total']}")
    print(f" Verified           : {summary['verified']}")
    print(f" GPA mismatches     : {summary['flags'].get('gpa_mismatch', 0)}")
    print(f" Missing rolls      : {summary['counts'].get('missing_roll', 0)}")
    print(f" Not found          : {summary['counts'].get('not_found', 0)}")
    print(f" Invalid reg/roll   : {summary['counts'].get('invalid_reg', 0)}")
    print(f" Failed/review      : {summary['counts'].get('failed', 0) + summary['counts'].get('ambiguous', 0)}")
    print(f" Elapsed            : {summary['elapsed']}")
    print(f" Output             : {summary['output']}")
    print(f" Marksheets         : {out_dir / 'marksheets.json'}")
    print(f" CSV                : {out_dir / 'marksheets.csv'}")
    print("=" * 64)
    if stopped_early:
        print(" Time cap reached. Resume with:")
        print(f"   /home/mushfiq/venv/bin/python3 {Path(__file__).name} --resume --out {out_dir}")
    log(
        log_path,
        f"done total={summary['total']} counts={summary['counts']} "
        f"verified={summary['verified']} elapsed={summary['elapsed']}",
        console=False,
    )


if __name__ == "__main__":
    main()
