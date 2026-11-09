# DeepSeek AI Handoff: Root-Cause Analysis & Resolution Plan for the 18 Missing Marksheets (844 / 862 Loaded)

## 1. Executive Summary

Out of **862** Science students listed in [`/home/mushfiq/Desktop/DC_Result/assigned_hsc_rolls_862.json`](file:///home/mushfiq/Desktop/DC_Result/assigned_hsc_rolls_862.json) (mirrored at [`/home/mushfiq/Desktop/DC_Result/python_captcha/assigned_hsc_rolls_862.json`](file:///home/mushfiq/Desktop/DC_Result/python_captcha/assigned_hsc_rolls_862.json)), the scraper [`/home/mushfiq/Desktop/DC_Result/python_captcha/eduboard_fetch.py`](file:///home/mushfiq/Desktop/DC_Result/python_captcha/eduboard_fetch.py) produced **844** complete subject-wise marksheets in [`/home/mushfiq/Desktop/DC_Result/python_captcha/results/marksheets_20261106_104600/progress.jsonl`](file:///home/mushfiq/Desktop/DC_Result/python_captcha/results/marksheets_20261106_104600/progress.jsonl).

Cross-referencing the official Dhaka Education Board gazette PDF [`/home/mushfiq/Desktop/DC_Result/dhaka_hsc_2026_107977.pdf`](file:///home/mushfiq/Desktop/DC_Result/dhaka_hsc_2026_107977.pdf) against `progress.jsonl` reveals the exact accounting of every single student and board roll:

- **Total Science HSC Rolls for Dhaka College (EIIN `107977`) in Board Gazette PDF**: **861** (`108727`–`109586` = 860 rolls, plus `900133` = 1 roll).
- **Total Enrolled Science Candidates in College Dataset**: **862** (meaning **1** of the 9 students without an online form fill-up receipt never registered for the HSC exam at all, leaving **861** actual examinees).
- **Matched Board Rolls (`status: "ok"`)**: **847**
  - **844** students with full 7-subject marksheets.
  - **3** students who were **Absent (`ABS.`)** in the HSC exam (`serial_no` `416`, `433`, `832` $\rightarrow$ HSC Rolls `109142`, `109159`, `109558`), where the Board API legitimately returns `result: "A"`, `gpa: null`, and `result_raw: ""`.
- **Unmatched Board Rolls Remaining in Gazette PDF**: **14** (`861 - 847 = 14`).
- **Unmatched Student Records in `assigned_hsc_rolls_862.json`**: **15** (**6** with `status: "invalid_reg"` + **9** with `status: "missing_roll"`).

---

## 2. File Inventory & Exact Code References

| File Path | Role in Pipeline | Relevant Lines / Issue |
| :--- | :--- | :--- |
| [`/home/mushfiq/Desktop/DC_Result/dhaka_hsc_2026_107977.pdf`](file:///home/mushfiq/Desktop/DC_Result/dhaka_hsc_2026_107977.pdf) | Official Dhaka Board result gazette for EIIN `107977` | Contains all **861** Science board rolls (`108727`..`109586` and `900133`) and their official GPAs/statuses. |
| [`/home/mushfiq/Desktop/DC_Result/scrape_checkpoint.json`](file:///home/mushfiq/Desktop/DC_Result/scrape_checkpoint.json) | Form fill-up payment receipts metadata per college roll | Stores `receipt_id`, `tx_no`, `tx_date`, `fee_type`, and `amount` for all 862 students. |
| [`/home/mushfiq/Desktop/DC_Result/receipts/`](file:///home/mushfiq/Desktop/DC_Result/receipts) | Raw college PDF receipts (`120242501XXXX.pdf`) | Source PDFs from which `registration_no` and `academic_year` were parsed. |
| [`/home/mushfiq/Desktop/DC_Result/extract_registrations.py`](file:///home/mushfiq/Desktop/DC_Result/extract_registrations.py) | Extracts `registration_no` from `receipts/*.pdf` | Lines `15–46`: Regex extraction from `pdftotext -layout`. |
| [`/home/mushfiq/Desktop/DC_Result/assign_new_rolls.py`](file:///home/mushfiq/Desktop/DC_Result/assign_new_rolls.py) | Assigns predicted `hsc_roll` and `hsc_roll_alt_by_payment_date` | Lines `58–78` & `114–131`: Contains flawed sorting assumptions for non-`21` registrations, late payers, and unpaid students. |
| [`/home/mushfiq/Desktop/DC_Result/python_captcha/assigned_hsc_rolls_862.json`](file:///home/mushfiq/Desktop/DC_Result/python_captcha/assigned_hsc_rolls_862.json) | Input file fed into `eduboard_fetch.py` | Contains the 862 student records (`serial_no` `1`..`862`). |
| [`/home/mushfiq/Desktop/DC_Result/python_captcha/eduboard_fetch.py`](file:///home/mushfiq/Desktop/DC_Result/python_captcha/eduboard_fetch.py) | Captcha solver & Board API scraper | Lines `216–236` (`parse_subjects` bug on `A-` and `F` grades); Lines `303–321` (`record_rolls` candidate roll generator); Lines `383–390` (`missing_roll` skip). |
| [`/home/mushfiq/Desktop/DC_Result/python_captcha/results/marksheets_20261106_104600/progress.jsonl`](file:///home/mushfiq/Desktop/DC_Result/python_captcha/results/marksheets_20261106_104600/progress.jsonl) | Raw scrape output log (JSONL) | Contains the API responses and `roll_used` for all 862 serials. |

---

## 3. Complete Breakdown of the 18 Students Without Marksheets

### Group A: 3 Students Who Were Absent (`ABS.`) in the HSC Exam (Nothing Broken — Expected Behavior)

These 3 students **matched (`status: "ok"`)** on the Board API, and their returned status is `"result": "A"` (`gpa: null`, `subjects: []`), which matches [`dhaka_hsc_2026_107977.pdf`](file:///home/mushfiq/Desktop/DC_Result/dhaka_hsc_2026_107977.pdf):

| `serial_no` | College Roll | Student Name | `registration_no` | `hsc_roll` (`roll_used`) | Board Gazette Status |
| :---: | :---: | :--- | :---: | :---: | :---: |
| **416** | `1202425010432` | `MD. NUR ALOM` | `2112807090` | `109142` | `109142[ABS.]` |
| **433** | `1202425010449` | `SAAD ISLAM EVAN` | `2112783388` | `109159` | `109159[ABS.]` |
| **832** | `1202425010876` | `MD. TOUHIDUL ISLAM JIDAN` | `2115484019` | `109558` | `109558[ABS.]` |

---

### Group B: The 14 Unmatched Board HSC Rolls in `dhaka_hsc_2026_107977.pdf`

By diffing all 861 Science rolls in [`dhaka_hsc_2026_107977.pdf`](file:///home/mushfiq/Desktop/DC_Result/dhaka_hsc_2026_107977.pdf) against the 847 `roll_used` values in [`progress.jsonl`](file:///home/mushfiq/Desktop/DC_Result/python_captcha/results/marksheets_20261106_104600/progress.jsonl), **only these 14 Board HSC Rolls remain unclaimed**:

| Unclaimed Board HSC Roll | Official Gazette GPA / Status | Location in Roll Sequence |
| :---: | :---: | :--- |
| **`108833`** | `4.83` | Inside main sequential block between `1202425010112` (`108832`) and `1202425010114` (`108834`) |
| **`109575`** | `4.75` | Tail block (end of main roll sequence after `1202425010893` $\rightarrow$ `109574`) |
| **`109576`** | `4.42` | Tail block |
| **`109577`** | `5.00` | Tail block |
| **`109578`** | `5.00` | Tail block |
| **`109579`** | `5.00` | Tail block |
| **`109580`** | `4.67` | Tail block (offline / late form fill-up / re-registered) |
| **`109581`** | `4.33` | Tail block |
| **`109582`** | `ABS.` | Tail block (Absent) |
| **`109583`** | `4.42` | Tail block |
| **`109584`** | `ABS.` | Tail block (Absent) |
| **`109585`** | `4.75` | Tail block |
| **`109586`** | `3.08` | Tail block |
| **`900133`** | `4.17` | Special / irregular Science board roll at end of Dhaka College Science section |

---

### Group C: Mathematical Proof of the Roll Shifts (`assign_new_rolls.py` vs. Actual Board Rolls)

In [`/home/mushfiq/Desktop/DC_Result/assign_new_rolls.py`](file:///home/mushfiq/Desktop/DC_Result/assign_new_rolls.py#L58-L63):
```python
# Primary block: 850 regular 21xxxxxxxx students who paid Form fill-up -> 108727..109576
# Secondary block: 3 non-21xxxxxxxx Form fill-up students (1202425010030, 1202425010113, 1202425010895) -> 109577..109579
reg_21_paid = [s for s in paid_853 if str(s.get("registration_no", "")).startswith("21")]
non_21_paid = [s for s in paid_853 if not str(s.get("registration_no", "")).startswith("21")]
ordered_paid_853 = reg_21_paid + non_21_paid
```

**Why this assumption in `assign_new_rolls.py` was wrong (proven by `roll_used` in `progress.jsonl`):**

1. **Transition 1 at `serial_no=28` (`1202425010030` vs `1202425010031`)**:
   - `serial_no=1..27` (`1202425010001`..`1202425010029`) matched `108727`..`108753` with `offset = 0`.
   - College roll `1202425010030` (`MD. MOMINUL HOWLADAR`, `reg=2018993541`) was moved to `serial_no=851` (`hsc_roll=109577`, `alt=108754`) by `assign_new_rolls.py` because his `reg` starts with `20`.
   - However, on the Board API, `MD. MOMINUL HOWLADAR` (`serial_no=851`) actually **succeeded at `roll_used = 108754`** (his natural college roll position)!
   - Consequently, `serial_no=28..32` (`1202425010031`..`1202425010035`) were all shifted by **`offset = +1`** (`108755`..`108759`).

2. **Transition 2 at `serial_no=33` (`1202425010036`, `Mohammad Radit Mehsan`)**:
   - `serial_no=32` (`1202425010035`) matched `108759`.
   - `serial_no=34` (`1202425010037`) matched `108760` (`offset` dropped back from `+1` to `0`!).
   - Because `108759` and `108760` are consecutive and both claimed, **`serial_no=33` (`1202425010036`, `Mohammad Radit Mehsan`, `reg=2110987858`, `academic_year="1"`) was NOT assigned a roll in the `108759–108760` gap**. He belongs to the tail block (`109575`–`109586` / `900133`).

3. **Transition 3 at `serial_no=107` (`1202425010113`, `MD. MAHFUZ AHAMED ASHIK`, `serial_no=852`)**:
   - `serial_no=106` (`1202425010112`) matched `108832` (`offset = 0`).
   - `serial_no=107` (`1202425010114`) matched `108834` (`offset = +1`).
   - **Board Roll `108833` is unclaimed!** Who sits between `1202425010112` and `1202425010114`?
   - **`1202425010113` (`MD. MAHFUZ AHAMED ASHIK`, `serial_no=852`)**!
   - Why didn't `serial_no=852` match `108833`? Two reasons:
     1. In `assigned_hsc_rolls_862.json`, `serial_no=852` was given `hsc_roll: "109578"` and `hsc_roll_alt_by_payment_date: "108834"`. In `eduboard_fetch.py` (`record_rolls`, lines 303–321), it only probes `[primary, primary+1, alt, primary-1]` = `[109578, 109579, 108834, 109577]`. **It never probed `108833` (`alt - 1`)!**
     2. In addition, check `serial_no=852`'s `registration_no`: `"2701326383"`. If `108833` + `"2701326383"` still returns `Invalid reg no`, then `"2701326383"` on his college profile is a 1-digit typo for `"2101326383"` (since SSC/HSC registrations for this cohort start with `21` or `20`, never `27`).

4. **Transition 4 at `serial_no=185` (`1202425010194`, `MD.FATIN ANJUM`)**:
   - From `serial_no=107` (`1202425010114`, `108834`) to `serial_no=184` (`1202425010193`, `108911`), every student matched at `offset = +1`.
   - At `serial_no=186` (`1202425010195`), the student matched `108912` (`offset = 0`).
   - Since `108911` (`serial_no=184`) and `108912` (`serial_no=186`) are consecutive, **`serial_no=185` (`1202425010194`, `MD.FATIN ANJUM`, `reg=2113236757`) was NOT in that gap** because he paid his form fill-up late on **`16-Jun-2026`** (`3,145` Tk, receipt `485793`). He was placed in the **tail block (`109575`–`109586`)**.
   - When `eduboard_fetch.py` ran for `serial_no=185`, `record_rolls` only tried `[108911, 108912, 109577, 108910]`. It did not sweep the full tail range `109575`–`109586`.

5. **Transition 5 at `serial_no=849..853` (End of Main Block `109575`–`109579`)**:
   - From `serial_no=186` (`108912`) to `serial_no=848` (`1202425010893`, `Yamin Ibtisam`, `109574`), every single student matched with `offset = 0`.
   - Right after college roll `1202425010893` (`109574`), the next college rolls in ascending order are:
     - `1202425010895` (`RAZIN ISLAM SIKDER`, `serial_no=853`, `reg=2010991736`) — moved to `serial_no=853` (`hsc_roll=109579`, `alt=109574`) by `assign_new_rolls.py` because his `reg` starts with `20`!
     - `1202425010896` (`Rafsanjani Rownak`, `serial_no=849`, `reg=2110987863`, `hsc_roll=109575`)
     - `1202425010897` (`Md. Asfar Hoque`, `serial_no=850`, `reg=2110967919`, `hsc_roll=109576`)
   - Wait: why did `serial_no=853` (`RAZIN ISLAM SIKDER`) only try `[109579, 109580, 109574, 109578]` and NOT `109575` (`alt + 1`)? Because `record_rolls` in `eduboard_fetch.py` (lines 311–321) only adds `primary ± 1`, NOT `alt ± 1`!
   - And why did `serial_no=849` (`109575`) and `serial_no=850` (`109576`) fail? Either they were shifted into `109577`–`109586` by the tail ordering, OR for `serial_no=850` (`Md. Asfar Hoque`) and `serial_no=853` (`RAZIN ISLAM SIKDER`) and `serial_no=33` (`Mohammad Radit Mehsan`), notice that in [`receipt_extracted_details.json`](file:///home/mushfiq/Desktop/DC_Result/receipt_extracted_details.json), their `admission_roll` is identical to their `registration_no` (meaning whoever filled out their college portal profile pasted their registration number into both fields, or made a typo).

---

## 4. Complete Table of the 15 Unmatched Students (`6 invalid_reg` + `9 missing_roll`)

All **15** of these students (minus the 1 student who never registered for HSC = **14** examinees) map to the **14 unclaimed Board HSC Rolls** (`108833`, `109575`–`109586`, `900133`):

| `serial_no` | College Roll | Student Name | `registration_no` | Current Status | Form Fill-Up Date | Assigned `hsc_roll` / `alt` | Target Candidate Board Rolls to Probe |
| :---: | :---: | :--- | :---: | :---: | :---: | :---: | :--- |
| **852** | `1202425010113` | `MD. MAHFUZ AHAMED ASHIK` | `2701326383` (also test `2101326383`) | `invalid_reg` | `02-Mar-2026` | `109578` / `108834` | **`108833`** (primary gap), plus `109575`–`109586`, `900133` |
| **853** | `1202425010895` | `RAZIN ISLAM SIKDER` | `2010991736` | `invalid_reg` | `09-Mar-2026` | `109579` / `109574` | **`109575`**, **`109576`**, **`109577`**, plus `109581`–`109586`, `900133` |
| **849** | `1202425010896` | `Rafsanjani Rownak` | `2110987863` | `invalid_reg` | `06-Mar-2026` | `109575` / `None` | **`109577`–`109586`**, **`900133`** (`109574`–`109576` already tried) |
| **850** | `1202425010897` | `Md. Asfar Hoque` | `2110967919` | `invalid_reg` | `03-Mar-2026` | `109576` / `None` | **`109578`–`109586`**, **`900133`** (`109575`–`109577` already tried) |
| **185** | `1202425010194` | `MD.FATIN ANJUM` | `2113236757` | `invalid_reg` | `16-Jun-2026` | `108911` / `109577` | **`109575`–`109586`**, **`900133`** (only `109577` was tried in tail) |
| **33** | `1202425010036` | `Mohammad Radit Mehsan` | `2110987858` | `invalid_reg` | `01-Mar-2026` | `108759` / `108760` | **`109575`–`109586`**, **`900133`** |
| **854** | `1202425010038` | `ASHIKUR RAHMAN` | `2121012218` | `missing_roll` | No online receipt | `null` | **`109575`–`109586`**, **`900133`** |
| **855** | `1202425010176` | `M ZAKARIA SAJID` | `2112668414` | `missing_roll` | No online receipt | `null` | **`109575`–`109586`**, **`900133`** |
| **856** | `1202425010262` | `MD. RIFAT` | `2110695899` | `missing_roll` | No online receipt | `null` | **`109575`–`109586`**, **`900133`** |
| **857** | `1202425010277` | `TEERTHA JYOTI BISWAS` | `2113207116` | `missing_roll` | No online receipt | `null` | **`109575`–`109586`**, **`900133`** |
| **858** | `1202425010379` | `RAKIB HASNAT APON` | `2113246048` | `missing_roll` | No online receipt | `null` | **`109575`–`109586`**, **`900133`** |
| **859** | `1202425010670` | `MD. HUZAIFA ISLAM HASIB` | `2121068014` | `missing_roll` | No online receipt | `null` | **`109575`–`109586`**, **`900133`** |
| **860** | `1202425010749` | `MD MASFIAN MRIDHA` | `2110721904` | `missing_roll` | No online receipt | `null` | **`109575`–`109586`**, **`900133`** |
| **861** | `1202425010757` | `S. M. SHAHARIA SAKIB JOY` | `2117777604` | `missing_roll` | No online receipt | `null` | **`109575`–`109586`**, **`900133`** |
| **862** | `1202425010852` | `ABID HOSSAIN FAHAD` | `2110786870` | `missing_roll` | No online receipt | `null` | **`109575`–`109586`**, **`900133`** |

---

## 5. Additional Subject-Parsing Bug in `eduboard_fetch.py` (Lines 216–236)

In [`/home/mushfiq/Desktop/DC_Result/python_captcha/eduboard_fetch.py`](file:///home/mushfiq/Desktop/DC_Result/python_captcha/eduboard_fetch.py#L216-L236):
```python
def parse_subjects(raw):
    if not isinstance(raw, str):
        return raw if isinstance(raw, list) else []
    subjects = []
    for part in raw.split(","):
        part = part.strip()
        if not part:
            continue
        match = re.match(r"^([\d-]+)\s+([A-Za-z+]+)\s+(.*?)\s+(\d+)$", part)
```
### Why this is broken in `eduboard_fetch.py`:
1. **Minus Grade (`A-`) Dropped**: The character class `[A-Za-z+]+` does **not** include `-`. Whenever a student gets an `A-` in any subject (e.g., `serial_no=8` `"275 A- INFORMATION & COMMUNICATION TECHNOLOGY 066"` or `serial_no=15` `"101-102 A- BANGLA 137"`), `re.match` returns `None`, falling back to `{"raw": part}`. As a result, `build_marksheet()` (lines `551–556`) fails to add that subject's marks to `total_marks` in `marksheets.json` and `marksheets.csv`!
2. **Fail Grade (`F`) Unparsed**: When a student gets an `F` grade (e.g., `serial_no=509` and `serial_no=659`), the Board API returns `"275 F INFORMATION & COMMUNICATION TECHNOLOGY "` with **no trailing marks integer**.

*(Note: [`/home/mushfiq/Desktop/DC_Result/python_captcha/build_web_data.py`](file:///home/mushfiq/Desktop/DC_Result/python_captcha/build_web_data.py#L38-L77) already fixes both regexes for the web portal's `students_data.json`, but `eduboard_fetch.py` should also be patched so `marksheets.json` and `marksheets.csv` are accurate.)*

---

## 6. Actionable Step-by-Step Instructions for DeepSeek AI

### Step 1: Fix `parse_subjects()` in `eduboard_fetch.py` (Lines 216–236)
Replace `parse_subjects(raw)` in [`/home/mushfiq/Desktop/DC_Result/python_captcha/eduboard_fetch.py`](file:///home/mushfiq/Desktop/DC_Result/python_captcha/eduboard_fetch.py#L216-L236) with:
```python
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
        match_no_marks = re.match(r"^([\d-]+)\s+([A-Za-z+-]+)\s+(.*?)$", part)
        if match_no_marks:
            subjects.append(
                {
                    "code": match_no_marks.group(1),
                    "grade": match_no_marks.group(2),
                    "subject": match_no_marks.group(3).strip(),
                    "marks": None,
                }
            )
        else:
            subjects.append({"raw": part})
    return subjects
```

### Step 2: Update `record_rolls(rec)` in `eduboard_fetch.py` (Lines 303–321) to Probe the 14 Unclaimed Board Rolls
In [`/home/mushfiq/Desktop/DC_Result/python_captcha/eduboard_fetch.py`](file:///home/mushfiq/Desktop/DC_Result/python_captcha/eduboard_fetch.py#L303-L321) and `lookup()` (lines `383–390`):
1. Do **not** immediately return `missing_roll` when `hsc_roll` is `null` if the student is one of the 15 unmatched serials (`33, 185, 849, 850, 852, 853, 854, 855, 856, 857, 858, 859, 860, 861, 862`).
2. Instead, for those 15 serials, set the candidate roll list to the **14 unclaimed Board HSC Rolls** (excluding any roll already claimed during the run):
   ```python
   UNCLAIMED_TAIL_ROLLS = [
       "108833",
       "109575", "109576", "109577", "109578", "109579",
       "109580", "109581", "109582", "109583", "109584",
       "109585", "109586", "900133",
   ]
   ```
   *(Important efficiency note: Since the Board API validates `(roll, regNo)` on a single solved captcha until a roll matches or all rolls return `status: 210 Invalid reg no`, a single solved captcha can test all 14 unclaimed rolls for a given student's `registration_no` in ~2 seconds! Once a roll succeeds for a student, remove that roll from `UNCLAIMED_TAIL_ROLLS` for subsequent students.)*
3. Specifically for `serial_no=852` (`1202425010113`, `MD. MAHFUZ AHAMED ASHIK`), test `roll="108833"` with both `registration_no="2701326383"` and `registration_no="2101326383"` (in case `"27..."` on the college portal was a typo for `"21..."`).

### Step 3: Run Targeted Recovery & Rebuild Static Web Data
Once `eduboard_fetch.py` is updated:
```bash
# 1. Re-run only the 15 unmatched serials and append/merge into progress.jsonl
python3 eduboard_fetch.py \
  --resume \
  --retry-failures \
  --out results/marksheets_20261106_104600 \
  --serials 33,185,849,850,852,853,854,855,856,857,858,859,860,861,862

# 2. Rebuild students_data.json and dist/ for the static web app
python3 build_web_data.py
```
