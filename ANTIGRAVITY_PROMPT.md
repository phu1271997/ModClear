# PROJECT CONTEXT PROMPT — ModClear (for Antigravity / AI IDE)

> Paste this so the agent understands product, architecture, and GenLayer constraints.
> Goal: keep “unicorn 4–5” orientation; never weaken consensus to schema-only.

---

## 1. What this is

**ModClear** = Intelligent Contract on **GenLayer**: neutral appellate court for platform content moderation. Creators file appeals; AI jury reads content + policy on-chain; rules UPHELD / OVERTURNED / PARTIAL.

**Pitch:** “No traditional SC can read a video and a policy page and judge a subjective violation — that *is* the product.”

## 2. Repo layout

```
contracts/mod_clear.py      # product core
contracts/storage_test.py   # deploy first
frontend/index.html         # genlayer-js dApp
frontend/src/config.js      # address + chain
frontend/samples/           # demo content/policy HTML
tests/test_mod_clear.py
scripts/deploy.sh
docs/
```

## 3. Lifecycle

```
file_appeal → FILED → adjudicate → RESOLVED
                ↑ request_retrial (once, bond)
                └───┘
RESOLVED → settle_fee → CLOSED
WIN → withdrawable credit → withdraw()
LOSE → treasury
```

## 4. Consensus (do not weaken)

- Use **`gl.eq_principle.prompt_comparative`** with WIN/LOSE equivalence principle.
- **Never** drop to schema-only validation or `return True` on LLM failure.
- Optional: one re-trial, platform reputation, pull-payment refunds.

## 5. Hard GenLayer rules

1. Line 1: `# v0.2.16`, line 2 Depends py-genlayer.  
2. No TreeMap/DynArray assign in `__init__`.  
3. No `float` in public signatures.  
4. Public types only: primitives, Address, DynArray, TreeMap.  
5. Storage TreeMap/DynArray only.  
6. Class name `Contract(gl.Contract)`.  
7. All `gl.nondet.*` inside eq_principle / run_nondet blocks.  
8. `from genlayer import *` only.

## 6. Deploy

- Studio: reset storage → storage_test → mod_clear → config.js  
- Live frontend: https://modclear-app.vercel.app  
- `bash scripts/deploy.sh testnet-asimov`

## 7. When editing

Ask: “Does this make the validator check shape instead of meaning? Break GenLayer rules? Make AI optional?” If yes — redesign.
