# Dhaka College HSC 2026 — Multi-Group Static Web Portal (`dist/`)

This directory is a self-contained static web bundle ready for deployment to GitHub Pages, Vercel, Netlify, or Cloudflare Pages.

## Directory Structure

```
dist/
├── index.html                  # Responsive multi-group portal entry point
├── styles.css                  # Responsive stylesheet (Desktop, Tablet, Mobile, Print)
├── app.js                      # Multi-group client engine & universal JSON normalizer
├── students_data.json          # Combined dataset + backward-compatible fallback
└── data/
    ├── manifest.json           # Registry of groups, file paths, and summary metadata
    ├── science.json            # Science division dataset (862 students, 850 marksheets)
    ├── humanities.json         # Humanities division dataset (143 Year-2 candidates ready)
    └── business_studies.json   # Business Studies division base slot
```

## How to Add or Update a Group's Results (e.g. Humanities / Business Studies)

### Option 1: Rebuild Automatically via `build_web_data.py` (Recommended)
Once marksheet scraping finishes (e.g. `progress.jsonl` or `marksheets.json` is saved in `hsc result humanities/` or `python_captcha/results/humanities_marksheets/`), run:
```bash
python3 python_captcha/build_web_data.py
```
This automatically merges student profiles with scraped marksheets, computes ranks and percentages, and updates `dist/data/humanities.json`, `dist/data/manifest.json`, and `dist/students_data.json`.

### Option 2: Direct JSON Drop-In to `dist/data/`
You can directly replace `dist/data/humanities.json` or `dist/data/business_studies.json` with any of the following formats:
1. **Built Web Format**: `{ "meta": { ... }, "students": [ ... ] }`
2. **Scraped Results Array**: `[ { "serial_no": 1, "roll": "1202425030001", "name": "...", "gpa": "5.00", "result_raw": "101-102 A+ BANGLA 165, ..." }, ... ]`
3. **JSONL Progress Output (`progress.jsonl`)**: The client-side normalizer in `app.js` parses raw JSONL lines on the fly and merges them with the base student names and college rolls.

Click the **Sync** button in the top header of the web app to refresh local cache and view the updated rankings.
