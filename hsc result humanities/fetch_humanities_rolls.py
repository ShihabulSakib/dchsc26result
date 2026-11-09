#!/usr/bin/env python3
"""
Fetch Dhaka College Humanities student profiles from eShiksa portal,
filter candidates by Academic Year 2, and extract Dhaka Board HSC 2026 results.
"""

import os
import sys
import json
import re
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed
import requests
from bs4 import BeautifulSoup

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(BASE_DIR)

CONTROLLER_URL = 'https://dhakacollege.eshiksabd.com/controller_student_module.php'
DEFAULT_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:153.0) Gecko/20100101 Firefox/153.0',
    'Accept': '*/*',
    'Accept-Language': 'en-US,en;q=0.9',
    'Referer': 'https://dhakacollege.eshiksabd.com/Basic-Result-Enquiry-Center',
    'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
    'X-Requested-With': 'XMLHttpRequest',
    'Origin': 'https://dhakacollege.eshiksabd.com',
    'Cookie': 'PHPSESSID=ssuc74296d32ct5ajbn76lrdoo'
}

def fetch_student(roll: str) -> dict | None:
    session = requests.Session()
    try:
        resp = session.post(
            CONTROLLER_URL,
            data={'rootData': str(roll), 'flagreq': 'profileRollCheck'},
            headers=DEFAULT_HEADERS,
            timeout=15
        )
        if 'No such class roll exists' in resp.text or 'Error' in resp.text:
            return None

        soup = BeautifulSoup(resp.text, 'html.parser')

        def get_val(label_text: str) -> str | None:
            lbl = soup.find(lambda t: t.name == 'label' and label_text in t.text)
            return lbl.find_next('label').text.strip() if lbl and lbl.find_next('label') else None

        img_tag = soup.find('img', id='studentImg')
        img_src = img_tag.get('src') if img_tag else None
        if img_src and not img_src.startswith('http'):
            img_src = 'https://dhakacollege.eshiksabd.com/' + img_src

        subjects = []
        tbody = soup.find('tbody', id='studentSubjectBody')
        if tbody:
            for tr in tbody.find_all('tr'):
                tds = tr.find_all('td')
                if len(tds) >= 3:
                    subjects.append({
                        'paper_1': tds[0].text.strip(),
                        'paper_2': tds[1].text.strip(),
                        'type': tds[2].text.strip()
                    })

        return {
            'roll': str(roll),
            'name': get_val('Name :'),
            'student_group': 'Humanities',
            'department': get_val('Department :'),
            'session': get_val('Session :'),
            'academic_year': get_val('Academic Year :'),
            'image_url': img_src,
            'subjects': subjects
        }
    except Exception as e:
        print(f"Error fetching roll {roll}: {e}", file=sys.stderr)
        return None

def main():
    print("Scraping Dhaka College HSC Humanities profiles (Session 2024-2025)...")
    rolls_to_check = [f"120242503{i:04d}" for i in range(1, 161)]
    students = []

    with ThreadPoolExecutor(max_workers=8) as executor:
        future_to_roll = {executor.submit(fetch_student, r): r for r in rolls_to_check}
        for future in as_completed(future_to_roll):
            res = future.result()
            if res:
                students.append(res)

    students.sort(key=lambda s: int(s['roll']))
    for idx, s in enumerate(students, 1):
        s['id'] = idx

    year2_students = [s for s in students if s['academic_year'] == '2']
    year1_students = [s for s in students if s['academic_year'] == '1']
    year2_rolls = [s['roll'] for s in year2_students]

    print(f"Total students found: {len(students)}")
    print(f"Academic Year 2 students: {len(year2_students)}")
    print(f"Academic Year 1 students: {len(year1_students)}")

    # Write output JSONs
    with open(os.path.join(BASE_DIR, 'rolls.json'), 'w', encoding='utf-8') as f:
        json.dump(year2_rolls, f, indent=2)

    with open(os.path.join(BASE_DIR, 'humanities_year2_rolls.json'), 'w', encoding='utf-8') as f:
        json.dump(year2_rolls, f, indent=2)

    with open(os.path.join(BASE_DIR, 'humanities_students_year2.json'), 'w', encoding='utf-8') as f:
        json.dump(year2_students, f, indent=2)

    with open(os.path.join(BASE_DIR, 'humanities_all_students.json'), 'w', encoding='utf-8') as f:
        json.dump(students, f, indent=2)

    with open(os.path.join(BASE_DIR, 'humanities_students_year1.json'), 'w', encoding='utf-8') as f:
        json.dump(year1_students, f, indent=2)

    # Dhaka Board HSC 2026 PDF result extraction if available
    pdf_candidates = [
        os.path.join(PROJECT_ROOT, 'dhaka_hsc_2026_107977.pdf'),
        os.path.join(PROJECT_ROOT, 'hsc result science', 'dhaka_hsc_2026_107977.pdf'),
        os.path.join(BASE_DIR, 'dhaka_hsc_2026_107977.pdf')
    ]
    for pdf_path in pdf_candidates:
        if os.path.exists(pdf_path):
            try:
                res = subprocess.run(['pdftotext', '-layout', pdf_path, '-'], capture_output=True, text=True)
                if ': HUMANITIES :' in res.stdout and ': SCIENCE :' in res.stdout:
                    hum_text = res.stdout.split(': HUMANITIES :')[1].split(': SCIENCE :')[0]
                    entries = re.findall(r'(\d{6})\[([^\]]+)\]', hum_text)
                    board_results = [{'board_roll': r, 'result': v.strip()} for r, v in entries]
                    with open(os.path.join(BASE_DIR, 'board_results_humanities_2026.json'), 'w', encoding='utf-8') as f:
                        json.dump(board_results, f, indent=2)
                    print(f"Extracted {len(board_results)} board results from {os.path.basename(pdf_path)}")
                    break
            except Exception as e:
                print(f"Could not parse PDF {pdf_path}: {e}", file=sys.stderr)

    print("Completed successfully!")

if __name__ == '__main__':
    main()
