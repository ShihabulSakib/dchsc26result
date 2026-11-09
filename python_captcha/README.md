# Education Board Result Scraper & Web App (`python_captcha`)

This directory contains the automated marksheet scraper for `eduboardresults.gov.bd` with an integrated computer-vision CAPTCHA solver and the static multi-cohort results web dashboard.

---

## 1. Requirements & Installation

### Python Packages

Install all required Python libraries via:

```bash
pip install -r requirements.txt
```

#### Core Dependencies:
- **`requests`** (`>=2.28.0`): HTTP session management with connection pooling and exponential backoff retry.
- **`numpy`** (`>=1.24.0`): Array operations on CAPTCHA images and contour coordinates.
- **`opencv-python`** (`>=4.8.0`): Morphological transforms, thresholding, and contour segmentation for CAPTCHA solving.
- **`Pillow`** (`>=9.5.0`): Image decoding and manipulation.
- **`beautifulsoup4`** (`>=4.12.0`): HTML table parsing for portal fee transactions.
- **`urllib3`** (`>=2.0.0`): Low-level HTTP connection handling and retry configuration.

### System Prerequisites (Linux / Debian / Ubuntu)
For receipt PDF text extraction and fallback OCR:
```bash
sudo apt update && sudo apt install -y poppler-utils tesseract-ocr
```

---

## 2. Key Programs

| Script | Purpose | Run Command |
| :--- | :--- | :--- |
| **`eduboard_fetch.py`** | Scrapes official board marksheets with automated CAPTCHA solving. | `python3 eduboard_fetch.py --input assigned_hsc_rolls_business.json --out results/business_marksheets` |
| **`captcha_new.py`** | Fast morphological OpenCV CAPTCHA solver module. | Imported by `eduboard_fetch.py` |
| **`build_web_data.py`** | Packages results into lightweight group JSONs and syncs `dist/`. | `python3 build_web_data.py` |
| **`app.js` / `index.html`** | Fast client-side results viewer with ranking and filtering. | Served via any static file server |

---

## 3. Running the Web App

To preview the dashboard locally:
```bash
python3 -m http.server 8000
```
Open **`http://localhost:8000`** in your browser.
