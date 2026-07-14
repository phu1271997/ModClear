# Studio verification — judge-required flow

> **Reviewer ask:** show that the submitted Studio contract deploys and completes  
> `file_appeal` → `adjudicate` → `get_appeal` → `settle_fee`, **or** fix TreeMap  
> key-type + SDK dependency lint issues.

This doc is the evidence checklist for resubmission.

---

## Lint fixes applied (vs original submission)

| Flag | Original problem | Fix in `contracts/mod_clear.py` |
|---|---|---|
| TreeMap key-type | `appeals: TreeMap[bigint, Appeal]` | `TreeMap[str, Appeal]` + `str(id)` keys (R19) |
| Storage struct | `@allow_storage` only | `@allow_storage` + `@dataclass` |
| SDK dependency | must be exact header | Line 1 `# v0.2.16`, line 2 official `Depends` py-genlayer hash, line 3 `from genlayer import *` |
| Consensus | custom `run_nondet_unsafe` soft-pass | `gl.eq_principle.prompt_comparative` on WIN/LOSE meaning |

All other maps also use **str** keys: `withdrawable`, `platform_total`, `platform_overturned`.

---

## Deployed contract (fill after each redeploy)

| Field | Value |
|---|---|
| Network | GenLayer Studio |
| Contract address | `0xBAc3555A32a47A4Af4518CcCb446dB49e73d1d25` *(update if redeployed after this lint pass)* |
| Source file | `contracts/mod_clear.py` |
| Live frontend | https://modclear-app.vercel.app |
| Repo | https://github.com/phu1271997/ModClear |

> If you redeploy after the dataclass lint fix, paste the **new** address into  
> `.env` / `frontend/src/config.js` and this table.

---

## Studio procedure (copy for evidence)

1. Open https://studio.genlayer.com/run-debug  
2. **Settings → Reset Storage → Confirm** → hard refresh  
3. Deploy `contracts/storage_test.py` → tx **Result: SUCCESS**  
4. Deploy `contracts/mod_clear.py` → tx **Result: SUCCESS** (not only FINALIZED)  
5. Confirm no lint errors on TreeMap keys / Depends  
6. Run the four methods below. Screenshot each tx Result + the `get_appeal` return.

### A. `file_appeal` (write, payable)

**value / fee:** `5000`

**args:**

| # | Type | Example |
|---|---|---|
| platform | str | `YouTube` |
| action_type | str | `DEMONETIZATION` |
| content_url | str | `https://modclear-app.vercel.app/samples/content-academic.html` |
| policy_url | str | `https://modclear-app.vercel.app/samples/policy-violence.html` |
| policy_quote | str | `Content that glorifies or incites violence will be demonetized.` |
| creator_statement | str | `Neutral academic overview; does not glorify or incite violence.` |

**Expect:** Result SUCCESS, appeal id `0` (or current `next_id`).

### B. `adjudicate` (write)

**args:** `appeal_id = 0`  
**Expect:** SUCCESS after consensus (may take 1–2 min). Status becomes `RESOLVED`.

### C. `get_appeal` (view)

**args:** `appeal_id = 0`  
**Expect:** JSON with at least:

```json
{
  "status": "RESOLVED",
  "ruling": "OVERTURNED | UPHELD | PARTIAL",
  "confidence": 0-100,
  "rationale": "<non-empty string>",
  "fee": 5000,
  "fee_refunded": false
}
```

### D. `settle_fee` (write)

**args:** `appeal_id = 0`  
**Expect:** SUCCESS, `status` = `CLOSED`, `fee_refunded` = true.  
- If ruling is OVERTURNED/PARTIAL → creator has withdrawable credit (`get_withdrawable`)  
- If UPHELD → `get_treasury` increased by fee  

Optional: `withdraw()` to pull refund.

---

## Evidence pack to attach in portal reply

1. Screenshot: deploy tx of `mod_clear.py` with **Result: SUCCESS** + address  
2. Screenshot: `file_appeal` SUCCESS  
3. Screenshot: `adjudicate` SUCCESS  
4. Screenshot / JSON: `get_appeal` showing ruling + rationale  
5. Screenshot: `settle_fee` SUCCESS + `get_appeal` status `CLOSED`  
6. Link: GitHub commit of fixed contract  
7. Link: live app pointing at that address  

### Short reply template for reviewers

```text
Thanks — lint and deploy path fixed.

1) TreeMap keys are now str (R19); storage structs use @allow_storage @dataclass;
   SDK header is # v0.2.16 + official py-genlayer Depends.

2) Studio contract: 0x… (paste address)
   Completed end-to-end:
   - file_appeal (fee 5000) → SUCCESS
   - adjudicate(0) → SUCCESS, status RESOLVED
   - get_appeal(0) → ruling=…, confidence=…, rationale present
   - settle_fee(0) → SUCCESS, status CLOSED

Screenshots: [attach]
Repo: https://github.com/phu1271997/ModClear
Live: https://modclear-app.vercel.app
```

---

## Local / CI tests (supporting, not a substitute for Studio)

```bash
gltest tests/test_mod_clear.py
```

Mocks cover the same path: file → adjudicate → get → settle (+ withdraw / retrial).
