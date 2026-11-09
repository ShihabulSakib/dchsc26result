# Dhaka College eShiksa – Result Enquiry POST Calls

Captured from Firefox DevTools (Network tab) on **Thu, 05 Nov 2026**.
Two POST calls to the same endpoint, with different request bodies.

- **Endpoint:** `https://dhakacollege.eshiksabd.com/controller_student_module.php`
- **Page that fires them:** `https://dhakacollege.eshiksabd.com/Basic-Result-Enquiry-Center`

> ⚠️ **Request bodies were not included in the capture.** Only headers were pasted. The bodies are 47 bytes (Call A) and 38 bytes (Call B). See [Missing data](#missing-data-needed-to-replay).

---

## 1. Call order (by timestamp)

| Order | Label | Server `Date` (response) | Request body size | Response size (decoded) |
|---|---|---|---|---|
| 1st | **Call A** | Thu, 05 Nov 2026 15:35:03 GMT | 47 B | 883 B |
| 2nd | **Call B** | Thu, 05 Nov 2026 15:39:06 GMT | 38 B | 32 B |

Call A was pasted second but happened first. If Call B depends on state set by Call A (e.g. a selected exam/class stored in the session), keep this order on the same session.

---

## 2. Call A (47-byte body, ~883 B response)

### Summary

| Field | Value |
|---|---|
| Method | `POST` |
| URL | `https://dhakacollege.eshiksabd.com/controller_student_module.php` |
| Status | `200 OK` |
| HTTP version | `HTTP/1.1` |
| Transferred | 891 B (883 B size) |
| Referrer Policy | `strict-origin-when-cross-origin` |
| Request Priority | `Highest` |
| DNS Resolution | `System` |

### Request headers (complete)

| Header | Value |
|---|---|
| Accept | `*/*` |
| Accept-Encoding | `gzip, deflate, br, zstd` |
| Accept-Language | `en-US,en;q=0.9` |
| Connection | `keep-alive` |
| Content-Length | `47` |
| Content-Type | `application/x-www-form-urlencoded; charset=UTF-8` |
| Cookie | `PHPSESSID=229qpckvq2pbr7823sbn78a63m` |
| Host | `dhakacollege.eshiksabd.com` |
| Origin | `https://dhakacollege.eshiksabd.com` |
| Priority | `u=0` |
| Referer | `https://dhakacollege.eshiksabd.com/Basic-Result-Enquiry-Center` |
| Sec-Fetch-Dest | `empty` |
| Sec-Fetch-Mode | `cors` |
| Sec-Fetch-Site | `same-origin` |
| User-Agent | `Mozilla/5.0 (X11; Linux x86_64; rv:153.0) Gecko/20100101 Firefox/153.0` |
| X-Requested-With | `XMLHttpRequest` |

### Response headers (complete)

| Header | Value |
|---|---|
| Cache-Control | `no-store, no-cache, must-revalidate` |
| Connection | `Keep-Alive` |
| Content-Encoding | `gzip` |
| Content-Length | `384` |
| Content-Type | `text/html; charset=UTF-8` |
| Date | `Thu, 05 Nov 2026 15:35:03 GMT` |
| Expires | `Thu, 19 Nov 1981 08:52:00 GMT` |
| Keep-Alive | `timeout=2, max=100` |
| Pragma | `no-cache` |
| Referrer-Policy | `strict-origin-when-cross-origin` |
| Server | `Apache/2.4.41 (Ubuntu)` |
| Vary | `Accept-Encoding` |
| X-Content-Type-Options | `nosniff` |
| X-Frame-Options | `SAMEORIGIN` |
| X-XSS-Protection | `1; mode=block` |

### Request body

```
<NOT CAPTURED – 47 bytes, application/x-www-form-urlencoded>
```

### Response body

```
<NOT CAPTURED – ~883 B of HTML after gzip decode, likely the actual result/data fragment>
```

---

## 3. Call B (38-byte body, ~32 B response)

### Summary

| Field | Value |
|---|---|
| Method | `POST` |
| URL | `https://dhakacollege.eshiksabd.com/controller_student_module.php` |
| Status | `200 OK` |
| HTTP version | `HTTP/1.1` |
| Transferred | 558 B (32 B size) |
| Referrer Policy | `strict-origin-when-cross-origin` |
| Request Priority | `Highest` |
| DNS Resolution | `System` |

### Request headers (complete)

| Header | Value |
|---|---|
| Accept | `*/*` |
| Accept-Encoding | `gzip, deflate, br, zstd` |
| Accept-Language | `en-US,en;q=0.9` |
| Connection | `keep-alive` |
| Content-Length | `38` |
| Content-Type | `application/x-www-form-urlencoded; charset=UTF-8` |
| Cookie | `PHPSESSID=229qpckvq2pbr7823sbn78a63m` |
| Host | `dhakacollege.eshiksabd.com` |
| Origin | `https://dhakacollege.eshiksabd.com` |
| Priority | `u=0` |
| Referer | `https://dhakacollege.eshiksabd.com/Basic-Result-Enquiry-Center` |
| Sec-Fetch-Dest | `empty` |
| Sec-Fetch-Mode | `cors` |
| Sec-Fetch-Site | `same-origin` |
| User-Agent | `Mozilla/5.0 (X11; Linux x86_64; rv:153.0) Gecko/20100101 Firefox/153.0` |
| X-Requested-With | `XMLHttpRequest` |

### Response headers (complete)

| Header | Value |
|---|---|
| Cache-Control | `no-store, no-cache, must-revalidate` |
| Connection | `Keep-Alive` |
| Content-Encoding | `gzip` |
| Content-Length | `52` |
| Content-Type | `text/html; charset=UTF-8` |
| Date | `Thu, 05 Nov 2026 15:39:06 GMT` |
| Expires | `Thu, 19 Nov 1981 08:52:00 GMT` |
| Keep-Alive | `timeout=2, max=100` |
| Pragma | `no-cache` |
| Referrer-Policy | `strict-origin-when-cross-origin` |
| Server | `Apache/2.4.41 (Ubuntu)` |
| Vary | `Accept-Encoding` |
| X-Content-Type-Options | `nosniff` |
| X-Frame-Options | `SAMEORIGIN` |
| X-XSS-Protection | `1; mode=block` |

### Request body

```
<NOT CAPTURED – 38 bytes, application/x-www-form-urlencoded>
```

### Response body

```
<NOT CAPTURED – 32 B after gzip decode, likely a short status/error/ID string>
```

---

## 4. Identical across both calls

Only `Content-Length`, `Date`, and response sizes differ. Everything else (method, URL, cookie, origin, referer, UA, fetch metadata) is the same.

## 5. Headers the agent must send vs. can skip

### Must / should send

| Header | Value | Why |
|---|---|---|
| Content-Type | `application/x-www-form-urlencoded; charset=UTF-8` | Required for PHP to parse the form body |
| X-Requested-With | `XMLHttpRequest` | Server likely checks for AJAX |
| Origin | `https://dhakacollege.eshiksabd.com` | Same-origin check |
| Referer | `https://dhakacollege.eshiksabd.com/Basic-Result-Enquiry-Center` | Same-origin / flow check |
| Cookie | `PHPSESSID=<session id>` | Session state |
| User-Agent | normal browser UA | Avoid bot blocking |
| Accept | `*/*` | Matches browser |

### Safe to skip (client sets automatically or irrelevant)

`Accept-Encoding`, `Accept-Language`, `Connection`, `Host`, `Content-Length`, `Priority`, `Sec-Fetch-Dest`, `Sec-Fetch-Mode`, `Sec-Fetch-Site`.

---

## 6. Replay templates

### Python (`requests`)

```python
import requests

BASE = "https://dhakacollege.eshiksabd.com"
URL = f"{BASE}/controller_student_module.php"
PAGE = f"{BASE}/Basic-Result-Enquiry-Center"

s = requests.Session()
s.headers.update({
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:153.0) Gecko/20100101 Firefox/153.0",
    "Accept": "*/*",
    "Accept-Language": "en-US,en;q=0.9",
    "X-Requested-With": "XMLHttpRequest",
    "Origin": BASE,
    "Referer": PAGE,
})

# Load the page first so the server issues a fresh PHPSESSID
s.get(PAGE)

# Call A (47-byte body) – fill in real fields
rA = s.post(URL, data={
    # "field": "value",
})
print("A:", rA.status_code, rA.text)

# Call B (38-byte body) – fill in real fields
rB = s.post(URL, data={
    # "field": "value",
})
print("B:", rB.status_code, rB.text)
```

### curl

```bash
# Call A
curl -s 'https://dhakacollege.eshiksabd.com/controller_student_module.php' \
  -H 'Content-Type: application/x-www-form-urlencoded; charset=UTF-8' \
  -H 'X-Requested-With: XMLHttpRequest' \
  -H 'Origin: https://dhakacollege.eshiksabd.com' \
  -H 'Referer: https://dhakacollege.eshiksabd.com/Basic-Result-Enquiry-Center' \
  -H 'Accept: */*' \
  -H 'User-Agent: Mozilla/5.0 (X11; Linux x86_64; rv:153.0) Gecko/20100101 Firefox/153.0' \
  -b 'PHPSESSID=YOUR_SESSION_ID' \
  --compressed \
  --data 'PASTE_CALL_A_BODY_HERE'

# Call B
curl -s 'https://dhakacollege.eshiksabd.com/controller_student_module.php' \
  -H 'Content-Type: application/x-www-form-urlencoded; charset=UTF-8' \
  -H 'X-Requested-With: XMLHttpRequest' \
  -H 'Origin: https://dhakacollege.eshiksabd.com' \
  -H 'Referer: https://dhakacollege.eshiksabd.com/Basic-Result-Enquiry-Center' \
  -H 'Accept: */*' \
  -H 'User-Agent: Mozilla/5.0 (X11; Linux x86_64; rv:153.0) Gecko/20100101 Firefox/153.0' \
  -b 'PHPSESSID=YOUR_SESSION_ID' \
  --compressed \
  --data 'PASTE_CALL_B_BODY_HERE'
```

### JSON spec for an AI agent / tool definition

```json
{
  "name": "dhakacollege_result_enquiry",
  "method": "POST",
  "url": "https://dhakacollege.eshiksabd.com/controller_student_module.php",
  "headers": {
    "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
    "X-Requested-With": "XMLHttpRequest",
    "Origin": "https://dhakacollege.eshiksabd.com",
    "Referer": "https://dhakacollege.eshiksabd.com/Basic-Result-Enquiry-Center",
    "Accept": "*/*",
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:153.0) Gecko/20100101 Firefox/153.0"
  },
  "cookies": { "PHPSESSID": "<fresh session id>" },
  "body_encoding": "form-urlencoded",
  "body_fields": "<TO FILL: copy from DevTools Request/Payload tab>",
  "response_type": "text/html (gzip)",
  "calls": [
    { "id": "A", "body_bytes": 47, "response_bytes": 883, "order": 1 },
    { "id": "B", "body_bytes": 38, "response_bytes": 32,  "order": 2 }
  ]
}
```

---

## 7. Notes and gotchas

1. **Session cookie.** `PHPSESSID=229qpckvq2pbr7823sbn78a63m` is tied to your browser session and will expire. Don't hardcode it; load the Referer page with a `Session` to get a fresh one. Treat it as private, since anyone holding it can act as that session.
2. **Order and state.** Run A then B on the same session unless the bodies show they're independent.
3. **Possible tokens/CAPTCHA.** Result portals often include a CAPTCHA, CSRF token, or hidden field in the body. If present in the bodies, the agent must fetch/solve it per request.
4. **Responses are HTML, not JSON.** Parse with BeautifulSoup or regex. `Content-Type` is `text/html` even though the call is AJAX.
5. **No caching.** Responses send `no-store, no-cache, must-revalidate` and a 1981 `Expires`, so every call hits the server.
6. **Rate limiting.** The server uses `Keep-Alive: timeout=2, max=100`. Reuse a session, but avoid hammering the endpoint.
7. **Use only as authorized.** Replay only for results you are entitled to look up.

---

## 8. Missing data needed to replay

In DevTools, click each request, then:

| Where | What to copy |
|---|---|
| **Request** (or **Payload**) tab → **Raw** | The exact body string (47 B for A, 38 B for B) |
| **Response** tab | The response HTML/text for each call |

Paste those and the template above can be completed and a response parser written.
