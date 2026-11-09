#!/usr/bin/env python3
"""Solve numeric captchas with WHITE digits on a DARK (curved/blurry) background.

Usage:  python captcha_digits.py captcha.jpeg [more.png ...] [--len 4] [--debug]
Needs:  pip install opencv-python numpy pytesseract   (+ the `tesseract` program)
"""
import argparse
from collections import Counter

import cv2
import numpy as np
import pytesseract

DIGITS = "0123456789"
CFG = "-c tessedit_char_whitelist=" + DIGITS


def make_mask(path, thr=225, kw=5, kh=3, scale=6, dil=2):
    """White digits -> 255. Removes white background corners, bridges the dark cut lines."""
    img = cv2.imread(path)
    if img is None:
        raise FileNotFoundError(path)
    g = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    m = (g > thr).astype(np.uint8) * 255
    H, W = m.shape
    n, lab, st, _ = cv2.connectedComponentsWithStats(m)
    for i in range(1, n):                     # big / border-touching white = background
        x, y, w, h, a = st[i]
        if x == 0 or y == 0 or x + w >= W or y + h >= H or a > 0.04 * H * W:
            m[lab == i] = 0
    m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_RECT, (kw, kh)))
    m = cv2.resize(m, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)
    m = cv2.GaussianBlur(m, (0, 0), scale * 0.5)
    m = (m > 110).astype(np.uint8) * 255
    if dil:
        m = cv2.dilate(m, np.ones((2 * dil + 1, 2 * dil + 1), np.uint8))
    n, lab, st, _ = cv2.connectedComponentsWithStats(m)   # drop specks
    out = np.zeros_like(m)
    for i in range(1, n):
        if st[i, cv2.CC_STAT_AREA] > 20 * scale * scale:
            out[lab == i] = 255
    return out


def split(m, n):
    """Cut into n digits at the emptiest columns near the evenly spaced positions."""
    proj = np.convolve((m > 0).sum(0).astype(float), np.ones(15) / 15, mode="same")
    cols = np.where(m.any(0))[0]
    x0, x1 = cols[0], cols[-1] + 1
    w = (x1 - x0) / n
    cuts = [x0]
    for i in range(1, n):
        c = int(x0 + i * w)
        lo, hi = int(c - w * .3), int(c + w * .3)
        cuts.append(lo + int(np.argmin(proj[lo:hi])))
    return cuts + [x1]


def ocr_digit(piece, psm, height, pad):
    rows, cols = np.where(piece.any(1))[0], np.where(piece.any(0))[0]
    if len(rows) == 0:
        return "?"
    p = piece[rows[0]:rows[-1] + 1, cols[0]:cols[-1] + 1]
    s = height / p.shape[0]
    p = (cv2.resize(p, None, fx=s, fy=s, interpolation=cv2.INTER_AREA) > 127).astype(np.uint8) * 255
    img = cv2.copyMakeBorder(255 - p, pad, pad, pad, pad, cv2.BORDER_CONSTANT, value=255)
    return pytesseract.image_to_string(img, config=f"--psm {psm} {CFG}").strip()[:1] or "?"


def ocr_line(m, psm):
    img = cv2.copyMakeBorder(255 - m, 30, 30, 30, 30, cv2.BORDER_CONSTANT, value=255)
    return pytesseract.image_to_string(img, config=f"--psm {psm} {CFG}").strip()


def solve(path, n=4, debug=False):
    pos = [Counter() for _ in range(n)]
    for thr in (215, 225):
        for kw, kh in ((3, 5), (5, 3), (5, 5)):
            for dil in (0, 2):
                m = make_mask(path, thr, kw, kh, 6, dil)
                if not m.any():
                    continue
                if debug and (thr, kw, kh, dil) == (225, 5, 3, 2):
                    cv2.imwrite("preprocessed.png", 255 - m)
                cuts = split(m, n)
                for i in range(n):                       # per-digit reads (main signal)
                    piece = m[:, cuts[i]:cuts[i + 1]]
                    for h in (80, 120):
                        for psm in (10, 13):
                            d = ocr_digit(piece, psm, h, 25)
                            if d != "?":                 # ignore "tesseract saw nothing"
                                pos[i][d] += 1
                for psm in (7, 8, 13):                   # whole-line reads (weak tie-breaker)
                    t = ocr_line(m, psm)
                    if len(t) == n:
                        for i, d in enumerate(t):
                            pos[i][d] += 0.1
    return "".join(c.most_common(1)[0][0] if c else "?" for c in pos), pos


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("images", nargs="+")
    ap.add_argument("--len", type=int, default=4, help="number of digits (default 4)")
    ap.add_argument("--debug", action="store_true", help="save preprocessed.png")
    a = ap.parse_args()
    for p in a.images:
        text, pos = solve(p, a.len, a.debug)
        print(f"{p}: {text}")
