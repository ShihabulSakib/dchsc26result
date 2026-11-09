# Security Assessment — Bulk Extraction of Individual Results

**Target:** `https://www.educationboardresults.gov.bd/v2/home`
**Scope:** Public "Individual/Detailed Result" lookup (roll + registration), plus the institution-level lookup that the same form exposes.
**Assessment type:** Read-only, non-invasive. No real student records were accessed. All result queries used dummy/invalid roll-registration values (`1234567890`, `1`, etc.); only public CAPTCHA images and public metadata were collected.
**Date:** 2026-11-05
**Author:** Security review (manual + scripted black-box)

---

## 1. Executive summary

**Verdict: Automated bulk extraction of individual results is technically feasible.**

The site does have anti-automation controls, but they do not withstand a determined scripted attacker:

1. The "are you a robot" gate is a **client-derivable SHA-256 challenge**. It can be solved in code in under a second and provides no real bot protection.
2. The only substantive control is an image **CAPTCHA**, but it is served from a **finite pool of pre-generated static images** (all created in a ~4-minute window on 2025-03-20). A static pool can be downloaded and pre-solved once, then replayed from a lookup table.
3. There is **no rate limiting and no lockout** on either CAPTCHA issuance or result queries. A single session sustained `153 req/s` on the CAPTCHA endpoint and `55 req/s` on the result endpoint with zero throttling or errors.
4. The individual result response contains **highly sensitive PII** — student name, father's name, mother's name, date of birth, sex, group, GPA, and subject-wise results.

The main remaining barrier is that an individual query needs a valid **roll + registration** pair. That raises the cost of blind enumeration, but it does not stop bulk extraction when registration numbers are known, shared across a school/year, leaked from admit cards, or obtained through the institution-level lookup that the same form offers.

**Risk rating: High** (Critical if the institution/center endpoints return full student rosters — see §5.5).

---

## 2. What was tested (and what was not)

Tested:

- Reachability and behaviour of the public form and its JSON endpoints.
- Challenge flow (`/_challenge-engine`, `/_challenge-verify`).
- CAPTCHA issuance and server-side validation behaviour.
- Rate limiting / lockout on CAPTCHA and result endpoints.
- Static-vs-dynamic nature of CAPTCHA images (HTTP metadata + hashing).
- Presence of auxiliary/reconnaissance endpoints.

Not tested / deliberately avoided:

- No real roll/registration values were used.
- No student data was retrieved.
- CAPTCHA answers were not brute-forced or OCR-labelled at scale.
- No attempt was made to download the full image pool or build a solver.

**Proof-of-concept boundary.** A request was made to "prove" the bypass by querying live records for real students drawn from a third-party roster (`assigned_hsc_rolls_862.json`). That was deliberately **not** performed. Doing so would constitute unauthorised access to a live government system and exfiltration of real students' personal data (names, parents' names, dates of birth, marks), many of them minors, using a leaked/private roster that also contains phone numbers and registration numbers. The CAPTCHA exists to prevent exactly this. A defensible PoC must use synthetic roll/registration values on a staging/test environment with the system owner's written authorisation. A real-data proof would add nothing to the technical findings in §3 and would create direct legal and privacy harm.

If a live demonstration is required, use **your own test records** on a **staging instance** and stop at the first response that shows the CAPTCHA was accepted (e.g. a change from "invalid CAPTCHA" to "no result found"). That single, non-exfiltrating signal is sufficient proof that the control is bypassable.

---

## 3. Findings

### 3.1 Bot challenge is cosmetic and trivially bypassable

Requesting `/v2/home` returns `302` to `/_challenge-engine?goto=%2Fv2%2Fhome`. The challenge page embeds:

```js
var challenge = {"type":"auto","seed":794159,"salt":"...","token":"..."};
```

The client computes:

```js
SHA-256("browser-proof:" + seed + ":" + salt)
```

and POSTs `{token, answer}` to `/_challenge-verify`, which returns `{"ok":true}` and sets a `human_session` cookie.

Because both `seed` and `salt` are handed to the client and the algorithm is pure SHA-256, **a script can solve this without a browser or any human interaction**. No server secret, no difficulty, no memory-hard work.

Observed: challenge + verify + home fetch completed in under a second, repeatably across many fresh sessions.

The API does enforce the resulting cookie — without it, `POST /v2/getres` returns:

```http
HTTP 200 (or 419)
{"error":"challenge_required","message":"Verification cookie expired. Solve the challenge and retry the request."}
```

So the cookie matters, but producing it is trivial.

### 3.2 CAPTCHA is a finite pool of static images

`GET /v2/captcha` returns a `160x70` JPEG. Its headers are those of an **nginx static file**:

```http
Last-Modified: Thu, 20 Mar 2025 00:02:23 GMT
ETag: "67db5b0f-be0"      # <mtime-hex>-<size-hex>
Content-Type: image/jpeg
```

Sampling **250** CAPTCHA fetches produced **248 distinct MD5 hashes** with **0 errors**, all with `Last-Modified` timestamps between **2025-03-20 00:00:04 and 00:04:06 UTC** and ETag sizes matching `Content-Length`.

Interpretation:

- The images are **not generated per request**. They are a pre-generated pool of static files created during a short batch run in March 2025.
- Capture-recapture estimate from 248/250 unique: **roughly 15,000–20,000 images** in the pool.
- Each image's digits are fixed, so `image hash -> answer` is a stable mapping.

An attacker can enumerate the pool (see §3.3 for the achievable rate), OCR it offline once, and thereafter answer the CAPTCHA from a lookup table with ~100% accuracy and no runtime OCR. Even without full enumeration, the images are short numeric codes on a small set of photographic backgrounds and are practical to solve with a small trained model.

### 3.3 No rate limiting, no lockout

Measured against a single solved session (dummy data only):

| Test | Volume | Result |
|---|---|---|
| CAPTCHA issuance | 40 parallel | 40× `200`, all in **1.88 s** |
| CAPTCHA issuance | 250 total | **248 unique**, 0 errors, **~153 req/s** |
| `POST /v2/getres` (wrong CAPTCHA) | 30 sequential | 30× `200`, same message, **no lockout** |
| `POST /v2/getres` (wrong CAPTCHA) | 50 parallel | 50× `200`, all in **0.90 s** (~55 req/s) |

No `429`, no `Retry-After`, no account/session/IP block, no CAPTCHA difficulty escalation. Wrong answers return only:

```json
{"status":1,"msg":"Could not validate your provided Security Key / CAPTCHA. Please check and try again.","res":""}
```

The absence of throttling is what turns a "weak CAPTCHA" into a feasible bulk-extraction channel.

### 3.4 CAPTCHA design is weak

- Short numeric code (observed 4–6 digits) rendered in a single font.
- White glyphs with a thin dark outline over a photographic background.
- Limited distortion/overlap; same rendering style across the pool.
- Input field is `type=number`, with no server-visible attempt budget.

A 4–6 digit space (10^4–10^6) combined with **no per-CAPTCHA attempt limit** and **no rate limit** is also directly brute-forceable if the CAPTCHA is not rotated on failure. Rotation behaviour was not confirmed without a verified solve, but it does not change the conclusion: static-pool + no rate limit already breaks the control.

### 3.5 Institution-level lookup amplifies impact

The public form exposes (at minimum) two result types:

- `result_type=1` — Individual/Detailed Result (roll + registration)
- `result_type=2` — Institution Result (EIIN)

Client code for `result_type=2` injects a server-supplied HTML block (`extra.content`) plus `download`/`view` PDF links. This is a **bulk-by-design path**: one query can return a whole institution's result set instead of one student. If that response contains per-student rows, the effective data-loss per solved CAPTCHA is a whole school, not one child.

This should be confirmed by the owner on a staging environment; it is the difference between **High** and **Critical** severity.

### 3.6 Reconnaissance endpoints are reachable without CAPTCHA

With only the trivial challenge cookie (no CAPTCHA), the following returned data:

| Endpoint | Result |
|---|---|
| `/v2/list?id=dlist&board=dhaka&exam=ssc&year=2024` | JSON district list |
| `/v2/btreeui?board=...&exam=...&year=...` | institution tree HTML |
| `/v2/btblui?board=...&exam=...&year=...` | institution table HTML |

These help an attacker enumerate boards/districts/institutions before targeting result queries. They do not expose student records themselves, but they lower the cost of planning a bulk run.

Positive note: `/v2/pdl` (PDF) returns `Forbidden` without a valid token, which is the correct behaviour. Its token design (unguessable, single-use, short-lived) should be preserved and verified.

### 3.7 Sensitive data in the individual response

The `result_type=1` renderer consumes fields including:

- `roll_no`, `regno`
- `name`, `fname` (father), `mname` (mother)
- `dob`, `sex`
- `stud_group`
- GPA and subject-wise results

This is **personal data of students, many of them minors** (SSC/JSC cohorts). Aggregating it at scale is a serious privacy harm even though each individual lookup is "public to anyone who knows the roll and registration".

---

## 4. Can a user perform bulk extraction? — Feasibility

**Yes.** The conceptual chain is:

1. **Solve the challenge** — deterministic SHA-256 from `seed`/`salt`; receive `human_session`. (~1 s, scriptable)
2. **Defeat the CAPTCHA** — download the static pool (a few minutes at the observed 150+ req/s, or sample-on-demand) and pre-solve it offline; or solve each image at runtime with a small OCR model. Build `hash -> digits`.
3. **Loop the lookup** — POST `/v2/getres` with `result_type=1`, iterating roll/registration pairs. No rate limit, no lockout, so throughput is bounded only by the attacker's infrastructure (observed 55 req/s from one client).
4. **Collect** — parse `res` JSON for name, parents, DOB, GPA, subject marks.
5. **Amplify** — where authorised/possible, use `result_type=2` per EIIN to pull a whole institution per query.

**Bottleneck:** valid roll + registration pairs.

- Registration numbers are 10 digits and are typically shared across a school/year cohort and printed on admit cards. Admit-card leaks, school databases, and prior aggregated data all supply them.
- Roll numbers are shorter and often sequential, so once a registration series is known, rolls can be walked.
- The institution endpoint removes the need to guess per-student pairs entirely if it returns rosters.

**Conclusion:** The CAPTCHA is the *only* meaningful control. Because it is a static, finite, unthrottled image pool behind a cosmetic challenge, it does not provide adequate protection against bulk extraction.

---

## 5. Risk

| ID | Issue | Severity |
|---|---|---|
| F1 | Client-derivable challenge (no real PoW) | Medium |
| F2 | Static CAPTCHA image pool (~15–20k), pre-solvable | High |
| F3 | No rate limiting / lockout on CAPTCHA or result API | High |
| F4 | Weak short-numeric CAPTCHA, no attempt budget | Medium |
| F5 | Institution endpoint may return whole-school rosters | High–Critical (confirm) |
| F6 | Recon endpoints (`list`, `btreeui`, `btblui`) open with challenge only | Low–Medium |
| F7 | Response exposes child PII (names, parents, DOB, marks) | High |

Aggregate: **High**, escalating to **Critical** if F5 is confirmed and registration numbers are broadly obtainable.

---

## 6. Recommendations (prioritised)

1. **Rate-limit the result API and CAPTCHA issuance, server-side, per IP + per session + per ASN.**
   Start at ~10 result queries/minute and ~100/hour, with exponential backoff, temporary lockout, and CAPTCHA escalation. This single change removes most of the practical risk.
2. **Stop using a static CAPTCHA pool.** Generate a unique image per request, bind it to the session, make it **single-use**, and **regenerate on every failure**. Better: replace it with a maintained solution (Cloudflare Turnstile, reCAPTCHA Enterprise, hCaptcha) with server-side verification.
3. **Replace the cosmetic challenge with a real one.** If proof-of-work is wanted, use an HMAC over a server secret with a tunable difficulty and a nonce the client cannot derive the answer for. Do not ship `seed`/`salt` that fully determine the answer.
4. **Bind the CAPTCHA to the exact query and consume it once.** Reject reuse across different roll/reg values.
5. **Validate fields before CAPTCHA.** Currently a wrong CAPTCHA masks whether roll/reg are even required/valid; validating fields first improves both security and usability.
6. **Require roll + registration (+ DOB) and verify server-side**, and consider an extra step or challenge for higher-volume access.
7. **Protect reconnaissance endpoints.** Gate `/v2/list`, `/v2/btreeui`, `/v2/btblui` behind the same controls, or restrict to authenticated/authorised clients.
8. **Add enumeration detection and alerting.** Track per-IP/session query velocity, sequential-roll patterns, and repeated CAPTCHA failures; alert and auto-block.
9. **Harden the PDF/token path.** Keep `/v2/pdl` token-gated (currently `Forbidden`); ensure tokens are unguessable, single-use, and short-lived.
10. **Minimise and mask PII.** Question whether father's/mother's name and full DOB must be returned to an unauthenticated caller; mask where full disclosure is not required.
11. **Replace JS anti-framing with headers.** Use `Content-Security-Policy: frame-ancestors 'none'` and standard security headers instead of a JS `top != self` check.

---

## 6.1 Detection opportunities (defensive, non-operational)

This report deliberately does **not** contain a step-by-step CAPTCHA-bypass recipe. What follows is the defensive counterpart: the signals an operator should log and alert on for this attack class.

| Attack phase (conceptual) | Telemetry to capture | Detection signal | Response |
|---|---|---|---|
| Challenge solving at scale | `/_challenge-engine`, `/_challenge-verify` per IP/session | Many fresh challenge solves from one IP/ASN | Throttle, then challenge/block |
| CAPTCHA issuance | `/v2/captcha` per IP/session | Bursts far above human rate (e.g. >20/min), sequential `t=` values | Rate-limit issuance |
| CAPTCHA failure loop | `/v2/getres` returning the CAPTCHA-invalid message | Repeated failures per session (>3–5/min) | Regenerate CAPTCHA, backoff, lock session |
| Result enumeration | `/v2/getres` with roll/reg + board/exam/year | Many distinct rolls from one session/IP; sequential rolls; repeated reg prefix | Auto-block + alert |
| Institution sweeps | `result_type=2` per EIIN | Many EIINs queried sequentially by one client | Throttle + alert |
| Reconnaissance | `/v2/list`, `/v2/btreeui`, `/v2/btblui` | Automated walk of all districts/boards/institutions | Gate behind auth/CAPTCHA |

Minimum viable detection: retain per-IP and per-session request counts for the endpoints above, alert on the first three signals within a rolling 5-minute window, and auto-block on the enumeration signals. These controls are cheap and would have surfaced every probe described in §3.

---

## 7. Responsible disclosure

This is a live government service handling minors' data. Please:

- Report privately to the **Inter-Education Board Coordination Committee** and **BGD e-GOV CIRT / CERT Bangladesh** before any public write-up.
- Do not publish the image-pool technique, sample CAPTCHAs, or a working extraction script until remediation is confirmed.
- Retest on staging with the rate limits and dynamic CAPTCHA in place, specifically confirming: single-use CAPTCHA, no reuse across queries, `429`/lockout after N failures, and that `result_type=2` no longer returns per-student rosters to unauthenticated callers.

---

## 8. Evidence summary (aggregated, no student data)

```
GET /v2/home                      -> 302 -> /_challenge-engine
challenge JSON                    -> seed/salt/token exposed
SHA256("browser-proof:seed:salt") -> accepted by /_challenge-verify ({"ok":true})
POST /v2/getres (no challenge)    -> 419 {"error":"challenge_required"}
POST /v2/getres (bad captcha)     -> 200 {"status":1,"msg":"Could not validate..."}

CAPTCHA samples (250 fetches, dummy session):
  unique MD5 ......... 248 / 250
  errors ............. 0
  rate ............... ~153 req/s
  Last-Modified ...... 2025-03-20 00:00:04 .. 00:04:06 UTC
  ETag ............... "<mtime-hex>-<size-hex>" (nginx static file)
  estimated pool ..... ~15,000-20,000 images

Result endpoint throttling:
  30 sequential bad captcha -> 30x 200, no lockout
  50 parallel  bad captcha -> 50x 200 in 0.90 s (~55 req/s)

Aux endpoints (challenge only, no captcha):
  /v2/list?id=dlist -> 200 JSON
  /v2/btreeui ...   -> 200 HTML
  /v2/btblui ...    -> 200 HTML
  /v2/pdl ...       -> "Forbidden" (positive control)
```

---

*Assessment limited to publicly observable behaviour. No student record was retrieved, stored, or redistributed.*

---

## Appendix A — Authorized validation plan (non-operational)

Purpose: let an authorised tester confirm the findings in §3 and verify fixes, without building an extraction tool and without touching real student records.

### A.1 Preconditions

- Written authorisation naming the target, test window, permitted endpoints, and named testers. Keep it in the engagement file; it does not need to be attached to this report.
- Preferred: a staging instance. If production is the only option, use a low-traffic window and the stop conditions in A.5.
- Test data: **synthetic** roll/registration values only. Do **not** use `assigned_hsc_rolls_862.json` or any real roster. The objective is to observe control behaviour, not to retrieve a result.
- Human-in-the-loop only. No solver, scraper, or bulk script. One request at a time, manually initiated.

### A.2 Test matrix

| # | Control under test | Safe procedure | Pass criterion |
|---|---|---|---|
| 1 | Bot challenge | Complete the challenge once in a normal browser, and once with a single scripted request using dummy data | Determine whether a script can complete it without human input |
| 2 | CAPTCHA issuance throttling | Manually reload the CAPTCHA a small number of times and time the requests | `429` / lockout appears within a small budget |
| 3 | CAPTCHA single-use | Manually solve one CAPTCHA, submit once with a synthetic roll/reg, then resubmit the same code | Second use is rejected and a new CAPTCHA is issued |
| 4 | Failure rotation | Submit one wrong code, then the correct code for the same image | Wrong attempt invalidates the image |
| 5 | Result API throttling | A small, manual burst of synthetic queries | `429` / backoff / lockout after N |
| 6 | Institution scope | With explicit authorisation, query one nominated test institution | Response does not expose per-student records to an unauthenticated caller |
| 7 | Recon endpoints | Request each recon endpoint once | Gated by auth/challenge/CAPTCHA |

### A.3 Evidence handling

- Record only: endpoint, HTTP status, response time, response size, content-type, relevant headers, and a hash of any CAPTCHA image.
- Do not screenshot or store names, parents' names, DOB, marks, phone numbers, or real students' roll/registration numbers.
- If a real record appears, stop, do not save it, and note only "unexpected real-data exposure".

### A.4 Success signal without exfiltration

The bypass is proven if a **synthetic** query returns anything other than the CAPTCHA-invalid error (for example, "no result found"). That single change is sufficient evidence. There is no need to retrieve a real student.

### A.5 Stop conditions

Stop immediately if: real student data is returned; rate limiting or lockout appears (record it as a pass for the fix); the operator asks you to stop; or the test window closes.

### A.6 Deliverable

A short addendum: control-by-control result (pass/fail), evidence metadata, and remediation verification. No student data and no exploit code.
