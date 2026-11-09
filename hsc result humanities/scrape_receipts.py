#!/usr/bin/env python3
"""
Scrape Form fill-up payment receipts (and fallback fee receipts for registration extraction)
for Dhaka College HSC Humanities students (Session 2024-2025).
"""

import json
import logging
import os
import re
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
import requests
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
INPUT_JSON = os.path.join(BASE_DIR, "humanities_all_students.json")
RECEIPTS_DIR = os.path.join(BASE_DIR, "receipts")
CHECKPOINT_FILE = os.path.join(BASE_DIR, "scrape_checkpoint.json")
PAID_JSON = os.path.join(BASE_DIR, "paid_humanities_students.json")
UNPAID_JSON = os.path.join(BASE_DIR, "unpaid_humanities_students.json")
UNPAID_ROLLS_JSON = os.path.join(BASE_DIR, "unpaid_rolls.json")

BASE_URL = "https://dhakacollege.eshiksabd.com"
MAIN_URL = f"{BASE_URL}/main"
LOGIN_URL = f"{BASE_URL}/Authentication"
ENQUIRY_URL = f"{BASE_URL}/Basic-Result-Enquiry-Center"
CONTROLLER_URL = f"{BASE_URL}/controller_student_module.php"
SLIP_URL = f"{BASE_URL}/std_coll_slip.php"

USERNAME = "dcstudent"
PASSWORD = "dcstudent"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(os.path.join(BASE_DIR, "scraper.log")),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

thread_local = threading.local()
checkpoint_lock = threading.Lock()


def create_authenticated_session() -> requests.Session:
    s = requests.Session()
    retries = Retry(
        total=5,
        backoff_factor=0.5,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET", "POST"]
    )
    adapter = HTTPAdapter(max_retries=retries, pool_connections=20, pool_maxsize=20)
    s.mount("https://", adapter)
    s.mount("http://", adapter)

    s.headers.update({
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:153.0) Gecko/20100101 Firefox/153.0",
        "Accept": "*/*",
        "Accept-Language": "en-US,en;q=0.9",
    })

    s.get(MAIN_URL, timeout=20)
    resp = s.post(
        LOGIN_URL,
        data={"username": USERNAME, "password": PASSWORD, "submit": "Sign In"},
        timeout=20
    )
    if "Invalid Username" in resp.text or resp.status_code != 200:
        raise RuntimeError(f"Login failed with status {resp.status_code}")

    s.headers.update({
        "X-Requested-With": "XMLHttpRequest",
        "Origin": BASE_URL,
        "Referer": ENQUIRY_URL,
    })
    return s


def get_session(force_relogin: bool = False) -> requests.Session:
    if force_relogin or not hasattr(thread_local, "session"):
        thread_local.session = create_authenticated_session()
    return thread_local.session


def parse_all_entries(html: str):
    """
    Parses the HTML table returned by transactionCheck.
    Returns (form_fillup_entries, all_entries).
    Even if a student didn't pay 'Form fill-up', downloading any receipt PDF
    still gives us their SSC/HSC Registration No!
    """
    soup = BeautifulSoup(html, "html.parser")
    form_fillup_entries = []
    all_entries = []
    for tr in soup.find_all("tr"):
        tds = tr.find_all("td")
        if len(tds) >= 7:
            student_name = tds[0].get_text(strip=True)
            bank_name = tds[1].get_text(strip=True)
            tx_no = tds[2].get_text(strip=True)
            tx_date = tds[3].get_text(strip=True)
            fee_type = tds[4].get_text(strip=True)
            amount = tds[5].get_text(strip=True)

            btn = tds[6].find("button")
            onclick = btn.get("onclick", "") if btn else str(tds[6])
            m = re.search(r"printReceipts\(\s*['\"]?(\d+)['\"]?\s*\)", onclick)
            if m:
                entry = {
                    "receipt_id": m.group(1),
                    "tx_no": tx_no,
                    "tx_date": tx_date,
                    "fee_type": fee_type,
                    "amount": amount,
                    "bank_name": bank_name,
                    "student_name_on_receipt": student_name
                }
                all_entries.append(entry)
                if "form fill-up" in fee_type.lower() or "form fill up" in fee_type.lower():
                    form_fillup_entries.append(entry)
    return form_fillup_entries, all_entries


def download_receipt_pdf(s: requests.Session, roll: str, entry: dict, filepath: str):
    receipt_id = entry["receipt_id"]
    rB = s.post(
        CONTROLLER_URL,
        data={"rootData": receipt_id, "flagreq": "ajaxEncryption"},
        timeout=20
    )
    rB.raise_for_status()
    xx_code = rB.text.strip()
    if not xx_code or "Error" in xx_code or "<html" in xx_code.lower():
        raise RuntimeError(f"Invalid xxCode for roll {roll}, receipt {receipt_id}: {xx_code[:100]}")

    rPDF = s.get(f"{SLIP_URL}?xxCode={xx_code}", timeout=30)
    rPDF.raise_for_status()
    if b"%PDF" not in rPDF.content[:32]:
        raise RuntimeError(f"Downloaded content for {roll} (receipt {receipt_id}) is not a valid PDF")

    with open(filepath, "wb") as f:
        f.write(rPDF.content)


def process_student(student: dict, max_attempts: int = 3) -> dict:
    roll = str(student["roll"]).strip()

    for attempt in range(1, max_attempts + 1):
        try:
            s = get_session(force_relogin=(attempt > 1))

            rA = s.post(
                CONTROLLER_URL,
                data={"rootData": roll, "flagreq": "transactionCheck"},
                timeout=20
            )
            rA.raise_for_status()
            textA = rA.text.strip()

            if "form-signin" in textA or 'action="Authentication"' in textA:
                s = get_session(force_relogin=True)
                rA = s.post(
                    CONTROLLER_URL,
                    data={"rootData": roll, "flagreq": "transactionCheck"},
                    timeout=20
                )
                rA.raise_for_status()
                textA = rA.text.strip()

            if "Error" in textA or "<table" not in textA:
                return {
                    "roll": roll,
                    "paid": False,
                    "reason": "no_payment_records",
                    "raw_response": textA[:200],
                    "files": [],
                    "entries": []
                }

            ff_entries, all_entries = parse_all_entries(textA)
            if not ff_entries:
                # Still download the first available receipt PDF if any exists so we can extract registration_no!
                primary_path = os.path.join(RECEIPTS_DIR, f"{roll}.pdf")
                if all_entries and not (os.path.exists(primary_path) and os.path.getsize(primary_path) > 1000):
                    download_receipt_pdf(s, roll, all_entries[0], primary_path)
                return {
                    "roll": roll,
                    "paid": False,
                    "reason": "missing_form_fill_up",
                    "other_fee_types": [e["fee_type"] for e in all_entries],
                    "files": [f"{roll}.pdf"] if all_entries else [],
                    "entries": [],
                    "all_entries": all_entries
                }

            saved_files = []
            multiple = len(ff_entries) > 1

            for idx, entry in enumerate(ff_entries):
                receipt_id = entry["receipt_id"]
                tx_no = re.sub(r"[^A-Za-z0-9_-]", "", entry["tx_no"]) or receipt_id
                filename = f"{roll}.pdf" if not multiple else f"{roll}_{tx_no}.pdf"
                filepath = os.path.join(RECEIPTS_DIR, filename)

                if os.path.exists(filepath) and os.path.getsize(filepath) > 1000:
                    with open(filepath, "rb") as f:
                        header = f.read(16)
                    if b"%PDF" in header:
                        saved_files.append(filename)
                        if multiple and idx == 0:
                            primary_path = os.path.join(RECEIPTS_DIR, f"{roll}.pdf")
                            if not os.path.exists(primary_path):
                                with open(filepath, "rb") as src, open(primary_path, "wb") as dst:
                                    dst.write(src.read())
                        continue

                download_receipt_pdf(s, roll, entry, filepath)
                if multiple and idx == 0:
                    primary_path = os.path.join(RECEIPTS_DIR, f"{roll}.pdf")
                    with open(filepath, "rb") as src, open(primary_path, "wb") as dst:
                        dst.write(src.read())
                saved_files.append(filename)

            return {
                "roll": roll,
                "paid": True,
                "reason": "paid",
                "files": saved_files,
                "entries": ff_entries
            }

        except Exception as e:
            logger.warning(f"Attempt {attempt}/{max_attempts} failed for roll {roll}: {e}")
            time.sleep(1.5 * attempt)

    return {
        "roll": roll,
        "paid": False,
        "reason": "scrape_error",
        "files": [],
        "entries": []
    }


def main():
    os.makedirs(RECEIPTS_DIR, exist_ok=True)
    with open(INPUT_JSON, "r", encoding="utf-8") as f:
        students = json.load(f)

    total = len(students)
    logger.info(f"Loaded {total} Humanities students from {INPUT_JSON}")

    results_by_roll = {}
    if os.path.exists(CHECKPOINT_FILE):
        try:
            with open(CHECKPOINT_FILE, "r", encoding="utf-8") as f:
                results_by_roll = json.load(f)
        except Exception:
            results_by_roll = {}

    with ThreadPoolExecutor(max_workers=12) as executor:
        future_to_st = {executor.submit(process_student, st): st for st in students}
        for fut in as_completed(future_to_st):
            res = fut.result()
            results_by_roll[res["roll"]] = res

    with open(CHECKPOINT_FILE, "w", encoding="utf-8") as f:
        json.dump(results_by_roll, f, ensure_ascii=False, indent=2)

    paid_students = []
    unpaid_students = []
    unpaid_rolls = []

    for st in students:
        roll = str(st["roll"]).strip()
        res = results_by_roll.get(roll, {})
        if res.get("paid"):
            paid_students.append(st)
        else:
            unpaid_rolls.append(roll)
            unpaid_entry = dict(st)
            unpaid_entry["unpaid_reason"] = res.get("reason", "unknown")
            if "other_fee_types" in res:
                unpaid_entry["other_fee_types"] = res["other_fee_types"]
            unpaid_students.append(unpaid_entry)

    with open(PAID_JSON, "w", encoding="utf-8") as f:
        json.dump(paid_students, f, ensure_ascii=False, indent=2)

    unpaid_payload = {
        "total_checked": total,
        "paid_count": len(paid_students),
        "unpaid_count": len(unpaid_students),
        "unpaid_rolls": unpaid_rolls,
        "students": unpaid_students
    }
    with open(UNPAID_JSON, "w", encoding="utf-8") as f:
        json.dump(unpaid_payload, f, ensure_ascii=False, indent=2)

    with open(UNPAID_ROLLS_JSON, "w", encoding="utf-8") as f:
        json.dump(unpaid_rolls, f, ensure_ascii=False, indent=2)

    logger.info(
        f"FINISHED! Total: {total} | Paid Form Fill-Up: {len(paid_students)} | Unpaid: {len(unpaid_students)}"
    )


if __name__ == "__main__":
    main()
