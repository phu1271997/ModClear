# Demo scenarios for ModClear

Three canned scenarios. Prefer the **frontend Demo buttons** (they point at
`frontend/samples/*.html` on the live host so `web.render` can fetch them).

---

## 1 — OVERTURNED (wrongful demonetization)

| Field | Value |
|---|---|
| Platform | YouTube |
| Action | DEMONETIZATION |
| Fee | 5000 |
| Content | `/samples/content-academic.html` |
| Policy | `/samples/policy-violence.html` |
| Quote | Content that glorifies or incites violence will be demonetized. |
| Statement | Neutral academic overview; no glorification/incitement. |
| Expected | **OVERTURNED** |

## 2 — UPHELD (real violation)

| Field | Value |
|---|---|
| Platform | TikTok |
| Action | REMOVAL |
| Content | `/samples/content-dangerous.html` |
| Policy | `/samples/policy-dangerous.html` |
| Quote | Content providing instructions to build dangerous devices is prohibited and will be removed. |
| Statement | “Educational only.” |
| Expected | **UPHELD** |

## 3 — PARTIAL (disproportionate strike)

| Field | Value |
|---|---|
| Platform | YouTube |
| Action | STRIKE |
| Content | `/samples/content-partial.html` |
| Policy | `/samples/policy-tiered.html` |
| Quote | Severe hateful content → strike; mild profanity → age-restrict. |
| Statement | Mild language, not hate; strike too heavy. |
| Expected | **PARTIAL** |

---

## Studio manual path

1. Deploy `mod_clear.py`.  
2. `file_appeal(...)` with `value = 5000`.  
3. `adjudicate(0)`.  
4. Optional `request_retrial(0)` with bond, then `adjudicate(0)` again.  
5. `get_appeal(0)` → ruling.  
6. `settle_fee(0)` → `withdraw()` if WIN.
