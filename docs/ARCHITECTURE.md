# Architecture — ModClear

## Overview

Single Intelligent Contract managing content-moderation appeal lifecycle, plus a static frontend calling it via `genlayer-js`. All adjudication happens **on-chain** through GenLayer’s AI validators.

## Data model

```
Contract
├── appeals: TreeMap[str, Appeal]     # str(appeal_id)
├── next_id: bigint
├── owner: Address
├── treasury: bigint
├── withdrawable: TreeMap[str, bigint]      # address hex → credit
├── platform_total: TreeMap[str, bigint]
└── platform_overturned: TreeMap[str, bigint]

Appeal
├── creator, platform, action_type
├── content_url, policy_url, policy_quote, creator_statement
├── fee, status, ruling, confidence, rationale, fee_refunded
├── appeal_round, previous_ruling, appealed
```

## State machine

```
file_appeal (payable)
      │
      ▼
  [FILED] ──adjudicate──▶ [REVIEWING] ──▶ [RESOLVED]
      ▲                                      │
      │         request_retrial (bond, once) │
      └──────────────────────────────────────┘
                                             │ settle_fee
                                             ▼
                                         [CLOSED]
                         WIN → credit withdrawable[creator]
                         LOSE → treasury
                         creator: withdraw()
```

## Consensus (`adjudicate`)

Uses **`gl.eq_principle.prompt_comparative`**, not byte-equal JSON.

1. Leader (and each validator re-running the block):
   - `web.render(content_url)` + `web.render(policy_url)` (unreachable → tagged string).
   - LLM returns `{ruling, confidence, rationale}` normalized to sorted JSON.
2. Equivalence principle:
   - Same **outcome class**: OVERTURNED|PARTIAL = WIN, UPHELD = LOSE.
   - Confidence within ~30 points.
   - Rationale wording may differ.

This is the Contract Quality differentiator: two validators can phrase reasons differently yet still agree the creator wins or loses.

## Edge cases

| Situation | Handling |
|---|---|
| Dead content/policy URL | `[UNREACHABLE]`, jury leans OVERTURNED |
| Invalid / unreadable LLM JSON | Normalized fallback or tx fails cleanly |
| fee = 0 / empty URLs / bad action | Rejected at `file_appeal` |
| settle twice | Blocked by `fee_refunded` |
| Second re-trial | Blocked by `appealed` / max rounds |
| Non-owner treasury | Rejected |
| Refund delivery | Pull-payment only |

## Frontend flow

1. File + fee  
2. Adjudicate (loading while FINALIZED)  
3. Optional re-trial  
4. Settle  
5. Withdraw  
6. Search verdict + platform stats  

Demo sample pages under `frontend/samples/` are absolute-URL fill-ins so `web.render` works on the live deploy.
