# ModClear — Decentralized Content Moderation Appeals Court

> An **Intelligent Contract** on GenLayer that turns every platform-moderation appeal into an on-chain AI jury verdict: validators **render the actioned content and the public policy page**, reason over both, and publish **UPHELD / OVERTURNED / PARTIAL** with confidence + rationale — public and immutable.

**One-line pitch (why this dies without GenLayer):**  
No traditional smart contract can read a video page and a natural-language policy, then decide “did this content actually violate *that* clause?” — subjective judgment over unstructured web data *is* the product. ModClear is the neutral appellate court platforms will never build for themselves.

| | |
|---|---|
| **Live app** | https://modclear-app.vercel.app |
| **GitHub** | https://github.com/phu1271997/ModClear |
| **Network** | GenLayer Studio / testnet (Bradbury era) |

---

## 1. The problem

Creators get **removed, demonetized, or struck** — often incorrectly. Platform appeals are a black box: slow, opaque, judged by the enforcer. Creators lose revenue with no neutral court.

The core question — *“does this content actually violate the cited policy clause?”* — is a **subjective judgment** over **unstructured** evidence.

## 2. Why GenLayer is the heart (not garnish)

| Capability | Role in ModClear |
|---|---|
| `gl.nondet.web.render` | Read content + policy pages **on-chain**, no oracle |
| `gl.nondet.exec_prompt` | LLM judges violation vs the **narrow** cited clause |
| `gl.eq_principle.prompt_comparative` | Validators agree on **meaning** (creator WIN vs LOSE), not JSON shape |
| Value transfers | Anti-spam deposit, refunds, treasury |

Strip AI + web access and there is **no product** — only a fee ledger.

## 3. Architecture

```
┌─────────────┐   genlayer-js    ┌────────────────────────┐
│  Frontend   │ ───────────────▶ │  ModClear (Python IC)  │
│ (index.html)│ ◀─────────────── │     on GenLayer        │
└─────────────┘   read state     └──────────┬─────────────┘
                                            │ adjudicate()
                                            ▼
                            ┌────────────────────────────────┐
                            │  AI Jury (validators)           │
                            │  • web.render(content)          │
                            │  • web.render(policy)           │
                            │  • LLM ruling + rationale       │
                            │  • prompt_comparative (meaning) │
                            └────────────────────────────────┘
```

**Lifecycle:**

```
file_appeal(payable) ──▶ FILED ──adjudicate──▶ RESOLVED
                              ▲                  │
                              │   request_retrial│ (bond, once)
                              └──────────────────┘
                                                 │ settle_fee
                                                 ▼
                                              CLOSED
                                    OVERTURNED/PARTIAL → withdrawable credit
                                    UPHELD → treasury
                                    creator calls withdraw()
```

### Contract quality highlights (scoring axis)

- Consensus via **`prompt_comparative`**, principle: same outcome class for the creator (WIN = OVERTURNED|PARTIAL, LOSE = UPHELD); confidence within 30 points; rationale wording may differ.
- **One-round re-trial** with bond before settle (self-authored escalation).
- **Pull-payment** refunds (`withdrawable` + `withdraw`) — no push-on-settle footguns.
- Edge cases: fee=0, bad `action_type`, empty URLs, double settle, non-owner treasury, unreachable pages (lean OVERTURNED).
- **Platform reputation** counters: total resolved + creator-favorable rate.

## 4. Repository layout

```
ModClear/
├── contracts/
│   ├── mod_clear.py         # Intelligent Contract (product core)
│   └── storage_test.py      # Deploy first to sanity-check the environment
├── frontend/
│   ├── index.html           # dApp (genlayer-js) — full user flow
│   ├── src/config.js        # CONTRACT_ADDRESS + CHAIN (build-generated)
│   └── samples/             # Public demo content + policy pages
├── tests/test_mod_clear.py
├── scripts/{deploy.sh,build-config.js}
├── docs/{ARCHITECTURE.md,COMMON_ERRORS.md,samples/SCENARIOS.md}
├── CHANGELOG.md
└── README.md
```

## 5. Deploy contract

### Studio (fastest for demo)

1. Open https://studio.genlayer.com/run-debug  
2. **Settings → Reset Storage → Confirm**, hard refresh.  
3. Deploy `contracts/storage_test.py` → expect SUCCESS.  
4. Deploy `contracts/mod_clear.py`.  
5. Copy address → set in `.env`:

```bash
GENLAYER_CONTRACT_ADDRESS=0xYourAddress
GENLAYER_CHAIN=studio
npm run build   # writes frontend/src/config.js
```

### CLI

```bash
bash scripts/deploy.sh testnet-asimov   # or localnet
```

## 6. Run frontend

```bash
cd frontend
npx serve .        # or: python3 -m http.server 8000
```

Open browser → **Connect Wallet** → use **Demo · OVERTURNED / UPHELD / PARTIAL** buttons → File → Adjudicate → (optional Re-trial) → Settle → Withdraw.

**Live:** https://modclear-app.vercel.app  

Deploy with Vercel (`vercel.json` builds `frontend/` via `npm run build`).

## 7. End-to-end demo (3 minutes)

1. Connect wallet.  
2. Click **Demo · OVERTURNED** (loads sample academic content + violence policy hosted under `/samples/`).  
3. **Deposit & Submit** (fee `5000`).  
4. **Run Adjudication** — wait for consensus (spinner).  
5. **Search** appeal `#N` — read ruling, confidence bar, AI rationale.  
6. **Settle Fee** → **Withdraw My Credit** if creator-favorable.  
7. Optional: **Platform Reputation** for `YouTube`.

More scenarios: [`docs/samples/SCENARIOS.md`](docs/samples/SCENARIOS.md).

## 8. Tests

```bash
gltest tests/test_mod_clear.py
```

Covers happy path, input validation, settle guards, owner-only treasury, re-trial once, pull-payment withdraw, platform stats (LLM/web mocks for nondet).

## 9. Public contract API

| Method | Kind | Purpose |
|---|---|---|
| `file_appeal(...)` *payable* | write | Open appeal + lock fee → `FILED` |
| `adjudicate(id)` | write | AI jury → `RESOLVED` |
| `request_retrial(id)` *payable* | write | One re-trial bond → back to `FILED` |
| `settle_fee(id)` | write | Credit refund or treasury → `CLOSED` |
| `withdraw()` | write | Pull creator refund credit |
| `withdraw_treasury(to, amount)` | write | Owner-only |
| `get_appeal(id)` | view | JSON state |
| `get_total_appeals()` | view | Count |
| `get_treasury()` | view | Treasury balance |
| `get_withdrawable(who)` | view | Refund credit |
| `get_platform_stats(platform)` | view | Overturn rate JSON |

## 10. Docs

- [`docs/STUDIO_VERIFICATION.md`](docs/STUDIO_VERIFICATION.md) — **judge path:** deploy + `file_appeal` → `adjudicate` → `get_appeal` → `settle_fee`  
- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md)  
- [`docs/COMMON_ERRORS.md`](docs/COMMON_ERRORS.md) — GenLayer deploy rules  
- [`CHANGELOG.md`](CHANGELOG.md)

### Reviewer notes (lint)

Original feedback flagged TreeMap key-type + SDK dependency. Current contract:

- `TreeMap[str, …]` only (never `bigint` keys)  
- `# v0.2.16` + official `Depends: py-genlayer:…`  
- `@allow_storage` + `@dataclass` on `Appeal`

---

*Built for the GenLayer Builder Program. Testnet details may change — verify at [docs.genlayer.com](https://docs.genlayer.com) before production deploy.*
