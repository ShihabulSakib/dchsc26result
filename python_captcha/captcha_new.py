#!/usr/bin/env python3
"""Solve 6-character captchas (colored letters + thin gray noise lines).

Usage:  python captcha_ocr.py img1.png [img2.png ...] [--len 6]
Needs:  pip install opencv-python numpy pytesseract   (+ the `tesseract` program)
Optional fallback if tesseract is missing:  pip install easyocr
"""
import argparse
import os
import shutil
from concurrent.futures import ThreadPoolExecutor
from collections import Counter

os.environ.setdefault("OMP_THREAD_LIMIT", "1")   # tesseract's own threads slow tiny images down

import cv2
import numpy as np

ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789"
HAVE_TESS = shutil.which("tesseract") is not None
if HAVE_TESS:
    import pytesseract


# ---------------------------------------------------------------- preprocessing
def load_image(src):
    if isinstance(src, np.ndarray):
        return src
    if isinstance(src, (bytes, bytearray)):
        return cv2.imdecode(np.frombuffer(src, np.uint8), cv2.IMREAD_COLOR)
    img = cv2.imread(src)
    if img is None:
        raise FileNotFoundError(src)
    return img


def clean_mask(src, scale=4, chroma_thr=40, white_thr=225, use_gray=True):
    """Return a binary mask (255 = letter) with the noise lines removed.

    Letters are either colored (high chroma) or thick gray strokes.
    Noise lines are thin and gray, so:
      colored pixels            -> keep
      other dark pixels         -> keep only if they survive a morphological
                                   opening wider than the line thickness
    """
    img = load_image(src)
    if img is None:
        raise FileNotFoundError(src)
    img = cv2.resize(img, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC).astype(int)
    chroma = img.max(2) - img.min(2)
    nonwhite = ((img.mean(2) < white_thr) | (chroma > chroma_thr)).astype(np.uint8) * 255
    colored = (chroma > chroma_thr).astype(np.uint8) * 255

    k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (scale + 1, scale + 1))
    thick = cv2.morphologyEx(nonwhite, cv2.MORPH_OPEN, k)
    mask = cv2.bitwise_or(colored, thick) if use_gray else colored

    # drop small specks
    n, lab, st, _ = cv2.connectedComponentsWithStats(mask)
    out = np.zeros_like(mask)
    for i in range(1, n):
        if st[i, cv2.CC_STAT_AREA] >= 6 * scale * scale:
            out[lab == i] = 255
    return out


def to_ocr_image(mask, pad=20):
    return cv2.copyMakeBorder(255 - mask, pad, pad, pad, pad, cv2.BORDER_CONSTANT, value=255)


# ------------------------------------------------------------------- OCR engines
def tess(img, psm):
    cfg = f"--psm {psm} -c tessedit_char_whitelist={ALPHABET}"
    return pytesseract.image_to_string(img, config=cfg).strip().replace(" ", "")


_easy = None
def easy(img):
    global _easy
    import easyocr
    if _easy is None:
        _easy = easyocr.Reader(["en"], gpu=False, verbose=False)
    return "".join(_easy.readtext(img, allowlist=ALPHABET, detail=0, paragraph=False))


def read_line(img):
    """All candidate strings for one preprocessed image."""
    if HAVE_TESS:
        return [tess(img, p) for p in (7, 8, 13)]
    return [easy(img)]


# --------------------------------------------------- fallback: per-character split
def split_chars(mask, n):
    """Cut the mask into n pieces at the emptiest columns near the expected cuts."""
    proj = (mask > 0).sum(0).astype(float)
    proj = np.convolve(proj, np.ones(5) / 5, mode="same")
    cols = np.where(mask.any(0))[0]
    x0, x1 = cols[0], cols[-1] + 1
    w = (x1 - x0) / n
    cuts = [x0]
    for i in range(1, n):
        c = int(x0 + i * w)
        lo, hi = int(c - w * 0.35), int(c + w * 0.35)
        cuts.append(lo + int(np.argmin(proj[lo:hi])))
    cuts.append(x1)
    return [mask[:, a:b] for a, b in zip(cuts[:-1], cuts[1:])]


def read_per_char(mask, n):
    out = ""
    for piece in split_chars(mask, n):
        cols = np.where(piece.any(0))[0]
        rows = np.where(piece.any(1))[0]
        if len(cols) == 0:
            out += "?"
            continue
        piece = piece[rows[0]:rows[-1] + 1, cols[0]:cols[-1] + 1]
        img = to_ocr_image(piece, 30)
        out += (tess(img, 10) if HAVE_TESS else easy(img))[:1] or "?"
    return out


# ------------------------------------------------- glyph boxes + case correction
# letters whose upper/lower case look identical except for size
SAME_SHAPE = set("cosuvwxzpy")
# pale letters differ from white by only ~20 levels; the gray noise lines by 0
CHROMA_THRS = (15, 35)
CONFUSIONS = {
    "0": "ODQ", "O": "0DQ", "D": "0O", "Q": "0O",
    "1": "IL", "I": "1L", "L": "1I",
    "2": "Z", "Z": "2",
    "5": "S", "S": "5",
    "6": "G", "G": "69",
    "8": "B", "B": "8",
    "9": "GQ", "U": "V", "V": "U",
    "M": "N", "N": "M",
}


def glyph_boxes(mask, n):
    """Return n (x, y, w, h) boxes, left to right, or None if the mask does not
    split cleanly into n glyphs. Boxes overlapping in x are merged (dots of i/j),
    and tiny leftovers of the noise lines are dropped."""
    num, _, st, _ = cv2.connectedComponentsWithStats(mask)
    boxes = sorted([tuple(st[i][:4]) + (st[i][4],) for i in range(1, num)])
    groups = []
    for x, y, w, h, a in boxes:
        if groups and x <= groups[-1]["x1"]:
            g = groups[-1]
            y0, y1 = min(g["y"], y), max(g["y"] + g["h"], y + h)
            g.update(x1=max(g["x1"], x + w), y=y0, h=y1 - y0, a=g["a"] + a)
        else:
            groups.append(dict(x=x, x1=x + w, y=y, h=h, a=a))
    if not groups:
        return None
    big = max(g["a"] for g in groups)
    groups = [g for g in groups if g["a"] > 0.15 * big]
    if len(groups) != n:
        return None
    return [(g["x"], g["y"], g["x1"] - g["x"], g["h"]) for g in groups]


def boxes_by_split(mask, n):
    """Fallback when glyphs touch each other / the noise: cut into n slices."""
    pieces = split_chars(mask, n)
    x, boxes = 0, []
    cols = np.where(mask.any(0))[0]
    x = cols[0]
    for piece in pieces:
        rows = np.where(piece.any(1))[0]
        if len(rows):
            boxes.append((x, rows[0], piece.shape[1], rows[-1] - rows[0] + 1))
        else:
            boxes.append((x, 0, piece.shape[1], 0))
        x += piece.shape[1]
    return boxes


def fix_case(text, boxes, raw_case):
    """s/S, c/C, o/O, v/V, w/W, x/X, z/Z ... look identical apart from size.
    Compare the glyph's TOP edge with the tops of the other glyphs (cap height);
    the top is more reliable than the height because noise lines inflate heights.
    Without a reference we keep the case Tesseract itself voted for."""
    refs = [b for ch, b in zip(text, boxes)
            if ch.lower() not in SAME_SHAPE and b[3] > 0] if boxes else []
    out = ""
    for i, ch in enumerate(text):
        if ch.lower() in SAME_SHAPE:
            if refs and boxes[i][3] > 0:
                cap_top = np.percentile([b[1] for b in refs], 25)
                cap_h = np.percentile([b[3] for b in refs], 25)
                lower = boxes[i][1] - cap_top > 0.15 * cap_h
            else:
                lower = raw_case[i].most_common(1)[0][0] == "l" if raw_case[i] else False
            ch = ch.lower() if lower else ch.upper()
        out += ch
    return out


# ----------------------------------------------------------------------- solving
def read_glyph(mask, box, psm, pad=30, grow=0):
    """OCR one glyph. `grow` thickens the strokes (px at the upscaled size);
    very thin glyphs such as a pale 'h' are misread as 'A' otherwise."""
    x, y, w, h = box
    piece = mask[max(0, y - 2):y + h + 2, max(0, x - 2):x + w + 2]
    if grow:
        piece = cv2.dilate(piece, cv2.getStructuringElement(
            cv2.MORPH_ELLIPSE, (2 * grow + 1, 2 * grow + 1)))
    img = to_ocr_image(piece, pad)
    return (tess(img, psm) if HAVE_TESS else easy(img))[:1]


def glyph_image(mask, box, grow=0, pad=30):
    x, y, w, h = box
    piece = mask[max(0, y - 2):y + h + 2, max(0, x - 2):x + w + 2]
    if grow:
        piece = cv2.dilate(piece, cv2.getStructuringElement(
            cv2.MORPH_ELLIPSE, (2 * grow + 1, 2 * grow + 1)))
    return to_ocr_image(piece, pad)


def solve(src, length=6, debug=False, max_workers=None, fast=False):
    pos = [Counter() for _ in range(length)]
    raw_case = [Counter() for _ in range(length)]
    line_votes = Counter()
    ref_boxes, ref_rank = None, -1
    jobs = []                                   # (position or None, weight, image, psm)

    if fast:
        configs = [(False, 4, CHROMA_THRS[0]), (False, 4, CHROMA_THRS[1])]
    else:
        configs = [(False, s, t) for s in (3, 4, 5) for t in CHROMA_THRS]
        configs += [(True, 4, t) for t in CHROMA_THRS]
    for use_gray, scale, thr in configs:
        mask = clean_mask(src, scale=scale, chroma_thr=thr, use_gray=use_gray)
        if not mask.any():
            continue
        boxes = glyph_boxes(mask, length)
        if not use_gray and boxes is None and not fast:
            continue                    # color-only lost a (gray) letter -> not usable
        if debug and scale == 4 and thr == 30:
            cv2.imwrite(f"preprocessed_{'gray' if use_gray else 'color'}.png",
                        to_ocr_image(mask))
        line_img = to_ocr_image(mask)
        for psm in ((7, 13) if HAVE_TESS else (0,)):
            jobs.append((None, 1, line_img, psm))
        if not boxes and use_gray:          # touching glyphs: use evenly cut slices
            boxes = boxes_by_split(mask, length)
            for i, b in enumerate(boxes):
                if b[3] > 0:
                    for psm in ((10, 13) if HAVE_TESS else (0,)):
                        jobs.append((i, 1, glyph_image(mask, b), psm))
            boxes = None
        if boxes:
            rank = 2 if not use_gray else 1
            if scale == 4 and thr == CHROMA_THRS[0] and rank > ref_rank:
                ref_boxes, ref_rank = boxes, rank
            w = 3 if not use_gray else 2
            for i, b in enumerate(boxes):
                grows = (0,) if fast else (0, scale)
                for grow in grows:          # normal + thickened strokes
                    gi = glyph_image(mask, b, grow)
                    for psm in ((10, 13) if HAVE_TESS else (0,)):
                        jobs.append((i, w, gi, psm))

    def run(job):
        _, _, img, psm = job
        return tess(img, psm) if HAVE_TESS else easy(img)

    if HAVE_TESS:
        workers = max_workers or min(3, os.cpu_count() or 1)
        with ThreadPoolExecutor(max_workers=workers) as ex:
            outs = list(ex.map(run, jobs))
    else:
        outs = [run(j) for j in jobs]

    def vote(i, ch, w):
        if not ch.isalnum():
            return
        pos[i][ch.upper() if ch.lower() in SAME_SHAPE else ch] += w
        if ch.isalpha():
            raw_case[i]["l" if ch.islower() else "u"] += w

    for (i, w, _, _), txt in zip(jobs, outs):
        txt = txt.strip().replace(" ", "")
        if i is None:                           # whole-line read: must be exactly `length`
            if len(txt) == length and txt.isalnum():
                line_votes[txt] += w
                for k, ch in enumerate(txt):
                    vote(k, ch, w)
        elif txt:
            vote(i, txt[0], w)

    if not any(pos[0]):
        return "?" * length, dict(line_votes)
    text = "".join(c.most_common(1)[0][0] if c else "?" for c in pos)
    if ref_boxes is None:                       # glyphs touch -> cut the mask into slices
        ref_boxes = boxes_by_split(clean_mask(src, 4, CHROMA_THRS[0]), length)
    return fix_case(text, ref_boxes, raw_case), dict(line_votes)


def solve_candidates(src, length=6, debug=False, max_workers=None, limit=12, fast=False):
    text, line_votes = solve(src, length, debug, max_workers, fast)
    cands = []

    def add(s):
        if len(s) == length and s.isalnum() and s not in cands:
            cands.append(s)

    add(text)
    for s, _ in sorted(line_votes.items(), key=lambda kv: kv[1], reverse=True)[:8]:
        add(s)
        if s.isupper():
            add(s.lower())
        elif s.islower():
            add(s.upper())

    for base in list(cands)[:4]:
        for i, ch in enumerate(base):
            for alt in CONFUSIONS.get(ch.upper(), ""):
                if ch.islower() and alt.isalpha():
                    alt = alt.lower()
                add(base[:i] + alt + base[i + 1:])
                if len(cands) >= limit:
                    return text, cands[:limit]
    return text, cands[:limit]


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("images", nargs="+")
    ap.add_argument("--len", type=int, default=6, help="captcha length (default 6)")
    ap.add_argument("--debug", action="store_true", help="save preprocessed.png")
    ap.add_argument("--workers", type=int, default=None, help="Tesseract worker threads")
    ap.add_argument("--candidates", action="store_true", help="print ranked candidates")
    ap.add_argument("--fast", action="store_true", help="use the reduced fast pipeline")
    a = ap.parse_args()
    if not HAVE_TESS:
        print("[!] tesseract not found, using EasyOCR (pip install easyocr)")
    for p in a.images:
        text, votes = solve(p, a.len, a.debug, a.workers, a.fast)
        print(f"{p}: {text}")
        if a.candidates:
            _, cands = solve_candidates(p, a.len, a.debug, a.workers, fast=a.fast)
            print("  candidates:", ", ".join(cands))
