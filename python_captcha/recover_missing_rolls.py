#!/usr/bin/env python3
import argparse
import json
import re
import subprocess
import time
from pathlib import Path

import captcha_new
import eduboard_fetch as ef


class RateLimited(Exception):
    pass


def pdf_rolls(pdf_path):
    path = Path(pdf_path)
    if not path.exists():
        return None
    try:
        text = subprocess.check_output(
            ["pdftotext", "-layout", str(path), "-"],
            text=True,
            errors="replace",
        )
    except Exception:
        return None
    seen = set()
    rolls = []
    for match in re.finditer(r"\b(\d{5,7})\[", text):
        roll = match.group(1)
        if roll not in seen:
            seen.add(roll)
            rolls.append(roll)
    return rolls or None


def science_rolls():
    rolls = [str(value) for value in range(108727, 109587)]
    rolls.append("900133")
    return rolls


def candidate_rolls(pdf_path):
    unclaimed = [str(value) for value in range(109579, 109587)]
    all_rolls = pdf_rolls(pdf_path) or science_rolls()
    return unclaimed + [roll for roll in reversed(all_rolls) if roll not in unclaimed]


def new_session():
    return ef.make_session()


def post_result(session, text, captcha_hash, timestamp, roll, reg, args):
    payload = {
        "rollNo": str(roll),
        "regNo": str(reg),
        "boardId": int(args.board),
        "passYear": int(args.year),
        "captchaText": text,
        "hash": captcha_hash,
        "timestamp": timestamp,
    }
    response = ef.request_with_retries(
        session,
        "POST",
        ef.RESULT_URL,
        retries=args.http_retries,
        timeout=args.timeout,
        json=payload,
    )
    if response.status_code != 200:
        return None, response
    try:
        return response.json(), response
    except ValueError:
        return None, response


def acquire_captcha(session, reg, probe_roll, args):
    for _ in range(8):
        try:
            image, captcha_hash, timestamp = ef.fetch_captcha(
                session, args.timeout, args.http_retries
            )
        except Exception:
            time.sleep(args.cooldown)
            continue
        best, candidates = captcha_new.solve_candidates(
            image,
            length=6,
            max_workers=args.captcha_workers,
            limit=12,
            fast=True,
        )
        if best not in candidates:
            candidates = [best] + candidates
        for text in candidates:
            if not text:
                continue
            data, _response = post_result(
                session, text, captcha_hash, timestamp, probe_roll, reg, args
            )
            if data is None:
                raise RateLimited
            message = str(data.get("message") or "").lower()
            if "invalid captcha" in message:
                continue
            return text, captcha_hash, timestamp
    return None


def read_last_progress(progress_path):
    last = {}
    if not progress_path.exists():
        return last
    for line in progress_path.read_text(encoding="utf-8").splitlines():
        try:
            item = json.loads(line)
        except json.JSONDecodeError:
            continue
        last[item.get("serial_no")] = item
    return last


def make_record(rec, roll, data, text, attempts, captcha_attempts, started, conflict_with=None):
    fields = ef.extract_fields(data)
    info = fields["info"]
    subjects = fields["result"] if isinstance(fields["result"], list) else []
    record = {
        "serial_no": rec.get("serial_no"),
        "id": rec.get("id"),
        "name": rec.get("name"),
        "registration_no": rec.get("registration_no"),
        "hsc_roll": rec.get("hsc_roll"),
        "hsc_roll_alt": rec.get("hsc_roll_alt_by_payment_date"),
        "expected_gpa": rec.get("board_gpa_or_status"),
        "student_group": rec.get("student_group"),
        "session": rec.get("session"),
        "roll_used": roll,
        "status": "ok",
        "returned_name": fields["name"],
        "returned_reg": fields["reg"],
        "gpa": fields["gpa"],
        "subjects_count": len(subjects),
        "info": info,
        "result": subjects,
        "result_raw": fields["result_raw"],
        "raw": data,
        "error": None,
        "attempts": attempts,
        "captcha_attempts": captcha_attempts,
        "captcha_text": text,
        "duration_s": round(time.time() - started, 2),
        "fetched_at": ef.now_stamp(),
    }
    if conflict_with is not None:
        record["conflict_with"] = conflict_with
    return record


def make_unresolved(rec, attempts, captcha_attempts, started, total_rolls):
    return {
        "serial_no": rec.get("serial_no"),
        "id": rec.get("id"),
        "name": rec.get("name"),
        "registration_no": rec.get("registration_no"),
        "hsc_roll": rec.get("hsc_roll"),
        "hsc_roll_alt": rec.get("hsc_roll_alt_by_payment_date"),
        "expected_gpa": rec.get("board_gpa_or_status"),
        "student_group": rec.get("student_group"),
        "session": rec.get("session"),
        "roll_used": None,
        "status": "missing_roll",
        "returned_name": None,
        "returned_reg": None,
        "gpa": None,
        "subjects_count": 0,
        "info": None,
        "result": None,
        "result_raw": None,
        "raw": None,
        "error": f"registration rejected on all {total_rolls} gazette rolls; likely unregistered",
        "attempts": attempts,
        "captcha_attempts": captcha_attempts,
        "captcha_text": None,
        "duration_s": round(time.time() - started, 2),
        "fetched_at": ef.now_stamp(),
        "bruteforce": True,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="assigned_hsc_rolls_862.json")
    parser.add_argument("--out", default="results/marksheets_20261106_104600")
    parser.add_argument(
        "--pdf", default="/home/mushfiq/Desktop/DC_Result/dhaka_hsc_2026_107977.pdf"
    )
    parser.add_argument("--serials", default="854,855,856,857,858,859,860,861,862")
    parser.add_argument("--board", type=int, default=10)
    parser.add_argument("--year", type=int, default=2026)
    parser.add_argument("--timeout", type=float, default=25)
    parser.add_argument("--http-retries", type=int, default=2)
    parser.add_argument("--captcha-workers", type=int, default=3)
    parser.add_argument("--delay", type=float, default=0.15)
    parser.add_argument("--batch", type=int, default=200)
    parser.add_argument("--cooldown", type=float, default=20)
    parser.add_argument("--max-refreshes", type=int, default=6)
    parser.add_argument("--limit-rolls", type=int, default=0)
    args = parser.parse_args()

    out_dir = Path(args.out)
    progress_path = out_dir / "progress.jsonl"
    records = ef.load_records(args.input)
    wanted = {int(value) for value in args.serials.split(",") if value.strip()}
    targets = [rec for rec in records if int(rec.get("serial_no", -1)) in wanted]
    targets.sort(key=lambda rec: int(rec.get("serial_no", 0)))

    last = read_last_progress(progress_path)
    roll_owners = {
        str(item.get("roll_used")): serial
        for serial, item in last.items()
        if item.get("status") == "ok" and item.get("roll_used")
    }
    rolls = candidate_rolls(args.pdf)
    print(f"candidate rolls: {len(rolls)}", flush=True)
    if args.limit_rolls:
        rolls = rolls[: args.limit_rolls]

    conflicts = []
    with open(progress_path, "a", encoding="utf-8") as jsonl:
        for rec in targets:
            serial = rec.get("serial_no")
            previous = last.get(serial) or {}
            if previous.get("status") == "ok":
                print(f"serial={serial} already ok", flush=True)
                continue
            reg = str(rec.get("registration_no") or "").strip()
            started = time.time()
            attempts = 0
            captcha_attempts = 0
            session = new_session()
            try:
                captcha = acquire_captcha(session, reg, rolls[0], args)
            except RateLimited:
                captcha = None
            captcha_attempts += 1
            if not captcha:
                print(f"serial={serial} could not acquire captcha", flush=True)
                continue
            text, captcha_hash, timestamp = captcha
            print(
                f"\nserial={serial} reg={reg} testing {len(rolls)} rolls",
                flush=True,
            )
            match = None
            completed = True
            for index, roll in enumerate(rolls, 1):
                try:
                    data, _response = post_result(
                        session, text, captcha_hash, timestamp, roll, reg, args
                    )
                except Exception:
                    data = None
                attempts += 1
                if data is None:
                    refreshed = False
                    for _ in range(args.max_refreshes):
                        print(
                            f"  rate limit at {index}/{len(rolls)}; cooling down {args.cooldown}s",
                            flush=True,
                        )
                        time.sleep(args.cooldown)
                        session = new_session()
                        try:
                            captcha = acquire_captcha(session, reg, rolls[0], args)
                        except RateLimited:
                            captcha = None
                        captcha_attempts += 1
                        if captcha:
                            text, captcha_hash, timestamp = captcha
                            refreshed = True
                            break
                    if not refreshed:
                        print(f"  giving up serial={serial} at roll={roll}", flush=True)
                        completed = False
                        break
                    try:
                        data, _response = post_result(
                            session, text, captcha_hash, timestamp, roll, reg, args
                        )
                    except Exception:
                        data = None
                    attempts += 1
                    if data is None:
                        continue
                message = str(data.get("message") or "").lower()
                if "invalid captcha" in message:
                    refreshed = False
                    for _ in range(args.max_refreshes):
                        session = new_session()
                        try:
                            captcha = acquire_captcha(session, reg, rolls[0], args)
                        except RateLimited:
                            captcha = None
                        captcha_attempts += 1
                        if captcha:
                            text, captcha_hash, timestamp = captcha
                            refreshed = True
                            break
                    if not refreshed:
                        completed = False
                        break
                    continue
                if data.get("status") == 200 and data.get("result"):
                    fields = ef.extract_fields(data)
                    returned_reg = ef.normalize_digits(fields["reg"])
                    expected_reg = ef.normalize_digits(reg)
                    similarity = ef.name_similarity(rec.get("name"), fields["name"])
                    if returned_reg == expected_reg or (similarity is not None and similarity >= 0.88):
                        conflict = roll_owners.get(str(roll))
                        if conflict is not None and conflict != serial:
                            conflicts.append((serial, roll, conflict))
                            print(
                                f"  CONFLICT serial={serial} roll={roll} already serial={conflict}",
                                flush=True,
                            )
                        match = (
                            roll,
                            data,
                            text,
                            conflict if conflict != serial else None,
                        )
                        print(
                            f"  MATCH serial={serial} roll={roll} "
                            f"name={fields['name']} reg={fields['reg']} gpa={fields['gpa']} "
                            f"sim={similarity}",
                            flush=True,
                        )
                        break
                if index % args.batch == 0:
                    print(
                        f"  progress {index}/{len(rolls)} attempts={attempts}",
                        flush=True,
                    )
                    time.sleep(args.cooldown)
                    session = new_session()
                    try:
                        captcha = acquire_captcha(session, reg, rolls[0], args)
                    except RateLimited:
                        captcha = None
                    captcha_attempts += 1
                    if not captcha:
                        completed = False
                        break
                    text, captcha_hash, timestamp = captcha
                time.sleep(args.delay)
            if match:
                roll, data, text, conflict_with = match
                record = make_record(
                    rec,
                    roll,
                    data,
                    text,
                    attempts,
                    captcha_attempts,
                    started,
                    conflict_with,
                )
                jsonl.write(json.dumps(record, ensure_ascii=False) + "\n")
                jsonl.flush()
                roll_owners[str(roll)] = serial
            elif completed:
                record = make_unresolved(
                    rec, attempts, captcha_attempts, started, len(rolls)
                )
                jsonl.write(json.dumps(record, ensure_ascii=False) + "\n")
                jsonl.flush()
                print(f"  UNRESOLVED serial={serial} attempts={attempts}", flush=True)
            else:
                print(
                    f"  INCOMPLETE serial={serial} attempts={attempts}; rerun this serial",
                    flush=True,
                )

    if conflicts:
        print("\nconflicts:", flush=True)
        for item in conflicts:
            print(item, flush=True)


if __name__ == "__main__":
    main()
