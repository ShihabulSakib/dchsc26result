#!/usr/bin/env python3
"""
Fetch Dhaka College Business Studies student profiles from eShiksa portal,
filter candidates by Academic Year 2, and extract Dhaka Board HSC 2026 results from gazette PDF.
"""

import os
import sys
import json
import re
import subprocess
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
import requests
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(BASE_DIR)

BASE_URL = "https://dhakacollege.eshiksabd.com"
MAIN_URL = f"{BASE_URL}/main"
LOGIN_URL = f"{BASE_URL}/Authentication"
ENQUIRY_URL = f"{BASE_URL}/Basic-Result-Enquiry-Center"
CONTROLLER_URL = f"{BASE_URL}/controller_student_module.php"

USERNAME = "dcstudent"
PASSWORD = "dcstudent"

thread_local = threading.local()


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


def fetch_student(roll: str) -> dict | None:
    for attempt in range(1, 4):
        try:
            session = get_session(force_relogin=(attempt > 1))
            resp = session.post(
                CONTROLLER_URL,
                data={"rootData": str(roll), "flagreq": "profileRollCheck"},
                timeout=20
            )
            if "form-signin" in resp.text or 'action="Authentication"' in resp.text:
                session = get_session(force_relogin=True)
                resp = session.post(
                    CONTROLLER_URL,
                    data={"rootData": str(roll), "flagreq": "profileRollCheck"},
                    timeout=20
                )

            if "No such class roll exists" in resp.text or "Error" in resp.text:
                return None

            soup = BeautifulSoup(resp.text, "html.parser")

            def get_val(label_text: str) -> str | None:
                lbl = soup.find(lambda t: t.name == "label" and label_text in t.text)
                return lbl.find_next("label").text.strip() if lbl and lbl.find_next("label") else None

            name = get_val("Name :")
            if not name:
                return None

            img_tag = soup.find("img", id="studentImg")
            img_src = img_tag.get("src") if img_tag else None
            if img_src and not img_src.startswith("http"):
                img_src = BASE_URL + "/" + img_src.lstrip("/")

            subjects = []
            tbody = soup.find("tbody", id="studentSubjectBody")
            if tbody:
                for tr in tbody.find_all("tr"):
                    tds = tr.find_all("td")
                    if len(tds) >= 3:
                        subjects.append({
                            "paper_1": tds[0].text.strip(),
                            "paper_2": tds[1].text.strip(),
                            "type": tds[2].text.strip()
                        })

            return {
                "roll": str(roll),
                "name": name,
                "student_group": "Business Studies",
                "department": get_val("Department :") or "HSC - Business Studies",
                "session": get_val("Session :") or "2024-2025",
                "academic_year": get_val("Academic Year :") or "2",
                "image_url": img_src,
                "subjects": subjects
            }
        except Exception as e:
            if attempt == 3:
                print(f"Error fetching roll {roll}: {e}", file=sys.stderr)
                return None
    return None


def extract_board_results():
    board_pdf = os.path.join(PROJECT_ROOT, "dhaka_hsc_2026_107977.pdf")
    if not os.path.exists(board_pdf):
        print("Board PDF not found at", board_pdf)
        return []

    try:
        res = subprocess.run(["pdftotext", "-layout", board_pdf, "-"], capture_output=True, text=True, check=True)
        text = res.stdout
        if ": BUSINESS STUDIES :" in text and ": HUMANITIES :" in text:
            bus_text = text.split(": BUSINESS STUDIES :")[1].split(": HUMANITIES :")[0]
            entries = re.findall(r"(\d{6})\[([^\]]+)\]", bus_text)
            board_results = [{"board_roll": r, "result": v.strip()} for r, v in entries]
            out_file = os.path.join(BASE_DIR, "board_results_business_2026.json")
            with open(out_file, "w", encoding="utf-8") as f:
                json.dump(board_results, f, indent=2, ensure_ascii=False)
            print(f"Extracted {len(board_results)} board results into board_results_business_2026.json")
            return board_results
    except Exception as e:
        print(f"Error parsing PDF: {e}", file=sys.stderr)
    return []


def main():
    print("Scraping Dhaka College HSC Business Studies profiles (Session 2024-2025)...")
    # Roll range: 1202425020001 to 1202425020150 (round figure 150)
    rolls_to_check = [f"120242502{i:04d}" for i in range(1, 151)]
    students = []

    with ThreadPoolExecutor(max_workers=10) as executor:
        future_to_roll = {executor.submit(fetch_student, r): r for r in rolls_to_check}
        for future in as_completed(future_to_roll):
            res = future.result()
            if res:
                students.append(res)

    students.sort(key=lambda s: int(s["roll"]))
    for idx, s in enumerate(students, 1):
        s["id"] = idx

    year2_students = [s for s in students if str(s["academic_year"]) == "2"]
    year1_students = [s for s in students if str(s["academic_year"]) == "1"]
    year2_rolls = [s["roll"] for s in year2_students]

    print(f"Total valid profiles found: {len(students)}")
    print(f"Academic Year 2 students: {len(year2_students)}")
    print(f"Academic Year 1 students: {len(year1_students)}")

    # Write output JSONs
    with open(os.path.join(BASE_DIR, "rolls.json"), "w", encoding="utf-8") as f:
        json.dump(year2_rolls, f, indent=2)

    with open(os.path.join(BASE_DIR, "business_year2_rolls.json"), "w", encoding="utf-8") as f:
        json.dump(year2_rolls, f, indent=2)

    with open(os.path.join(BASE_DIR, "business_students_year2.json"), "w", encoding="utf-8") as f:
        json.dump(year2_students, f, indent=2, ensure_ascii=False)

    with open(os.path.join(BASE_DIR, "business_all_students.json"), "w", encoding="utf-8") as f:
        json.dump(students, f, indent=2, ensure_ascii=False)

    with open(os.path.join(BASE_DIR, "business_students_year1.json"), "w", encoding="utf-8") as f:
        json.dump(year1_students, f, indent=2, ensure_ascii=False)

    extract_board_results()
    print("Profile fetching complete!")


if __name__ == "__main__":
    main()
