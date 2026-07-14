# v0.2.16
# { "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }
from genlayer import *

import json


# =============================================================================
# ModClear - Decentralized Content Moderation Appeals Court
#
# Problem: Creators get content removed, demonetized, or struck by platforms
# (YouTube, TikTok, X...) - often incorrectly. Platform appeals are a black box:
# slow, opaque, and judged by the same party that enforced. Creators lose revenue
# with no neutral court.
#
# Solution: Every appeal becomes an on-chain AI Jury verdict.
# 1. Creator files appeal + deposit (anti-spam; refunded on win).
# 2. AI Jury reads content_url + policy_url on-chain (web.render + LLM) and rules
#    UPHELD / OVERTURNED / PARTIAL with confidence + rationale.
# 3. Consensus uses prompt_comparative on MEANING (same ruling class), not JSON
#    shape. Validators may phrase rationale differently and still agree.
# 4. Optional one-round appeal re-runs the jury with a bond.
# 5. Settle credits refunds via pull-payment; UPHELD fees go to treasury.
# 6. Platform reputation counters track overturn rate for transparency.
#
# Why GenLayer: Deciding if unstructured content violates a natural-language
# policy is subjective and requires live web access. Solidity cannot do this.
# AI + web is the product heart, not garnish.
# =============================================================================


APPEAL_FILED = "FILED"
APPEAL_REVIEWING = "REVIEWING"
APPEAL_RESOLVED = "RESOLVED"
APPEAL_CLOSED = "CLOSED"

RULING_UPHELD = "UPHELD"
RULING_OVERTURNED = "OVERTURNED"
RULING_PARTIAL = "PARTIAL"

VALID_ACTIONS = ("REMOVAL", "DEMONETIZATION", "STRIKE", "AGE_RESTRICT")
VALID_RULINGS = (RULING_UPHELD, RULING_OVERTURNED, RULING_PARTIAL)

# Validators must agree the appeal outcome is the same class for the creator:
# WIN (OVERTURNED/PARTIAL) vs LOSE (UPHELD). Rationale wording may differ.
EQUIVALENCE_PRINCIPLE = (
    "Both answers must reach the SAME substantive outcome for the creator. "
    "Treat OVERTURNED and PARTIAL as creator-favorable (WIN). Treat UPHELD as "
    "platform-favorable (LOSE). The two answers are equivalent only if both are "
    "WIN or both are LOSE. Confidence may differ by at most 30 points. "
    "Rationale wording may differ; the decision class must not."
)

MAX_APPEALS = 1  # one re-trial after the first verdict


def _addr_hex(addr: Address) -> str:
    try:
        return addr.as_hex
    except Exception:
        return str(addr)


def _to_address(s: str) -> Address:
    if not s.startswith("0x"):
        s = "0x" + s
    return Address(s)


def _clamp_conf(v: int) -> int:
    if v < 0:
        return 0
    if v > 100:
        return 100
    return v


def _normalize_ruling(raw: str) -> str:
    r = str(raw or "").strip().upper()
    if r in VALID_RULINGS:
        return r
    return ""


def _creator_wins(ruling: str) -> bool:
    return ruling in (RULING_OVERTURNED, RULING_PARTIAL)


@allow_storage
class Appeal:
    creator: Address
    platform: str
    action_type: str
    content_url: str
    policy_url: str
    policy_quote: str
    creator_statement: str
    fee: bigint

    status: str
    ruling: str
    confidence: bigint
    rationale: str
    fee_refunded: bool

    # Escalation / quality
    appeal_round: bigint       # 0 = initial, 1 = after one re-trial
    previous_ruling: str       # ruling before the re-trial ("" if none)
    appealed: bool             # True after the optional re-trial has been filed


class Contract(gl.Contract):
    # Storage. DO NOT initialize TreeMap/DynArray in __init__ (Rule #2).
    # Keys are str(appeal_id) for TreeMap key safety across GenVM builds.
    appeals: TreeMap[str, Appeal]
    next_id: bigint
    owner: Address
    treasury: bigint
    # Pull-payment credits (address hex -> amount)
    withdrawable: TreeMap[str, bigint]
    # Platform reputation counters (platform name -> count)
    platform_total: TreeMap[str, bigint]
    platform_overturned: TreeMap[str, bigint]

    def __init__(self):
        self.next_id = bigint(0)
        self.owner = gl.message.sender_address
        self.treasury = bigint(0)

    # === Helpers ===

    def _err(self, msg: str) -> None:
        # Prefer UserError when available; fall back for older GenVM builds.
        try:
            raise gl.vm.UserError(msg)
        except AttributeError:
            raise Exception(msg)

    def _require(self, cond: bool, msg: str) -> None:
        if not cond:
            self._err(msg)

    def _get_appeal(self, appeal_id: int) -> Appeal:
        key = str(appeal_id)
        if key not in self.appeals:
            self._err("Appeal not found")
        return self.appeals[key]

    def _credit(self, to: Address, amount: bigint) -> None:
        if amount <= bigint(0):
            return
        key = _addr_hex(to)
        prev = self.withdrawable[key] if key in self.withdrawable else bigint(0)
        self.withdrawable[key] = prev + amount

    def _bump_platform_stats(self, platform: str, ruling: str) -> None:
        name = (platform or "unknown").strip() or "unknown"
        total = self.platform_total[name] if name in self.platform_total else bigint(0)
        self.platform_total[name] = total + bigint(1)
        if _creator_wins(ruling):
            ov = (
                self.platform_overturned[name]
                if name in self.platform_overturned
                else bigint(0)
            )
            self.platform_overturned[name] = ov + bigint(1)

    # === Non-deterministic core: AI Jury ===

    def _run_jury(
        self,
        platform: str,
        action_type: str,
        content_url: str,
        policy_url: str,
        policy_quote: str,
        creator_statement: str,
        appeal_round: int,
        previous_ruling: str,
    ) -> str:
        """
        Leader produces JSON; validators re-run the same block and agree via
        prompt_comparative on MEANING (creator WIN vs LOSE), not byte-equal JSON.
        Returns a normalized JSON string.
        """

        def leader_fn() -> str:
            try:
                content_page = gl.nondet.web.render(content_url, mode="text")
            except Exception:
                content_page = "[UNREACHABLE: could not load the content URL]"
            try:
                policy_page = gl.nondet.web.render(policy_url, mode="text")
            except Exception:
                policy_page = "[UNREACHABLE: could not load the policy URL]"

            prior = ""
            if appeal_round > 0 and previous_ruling:
                prior = (
                    f"\nTHIS IS RE-TRIAL ROUND {appeal_round}. "
                    f"Previous on-chain ruling was {previous_ruling}. "
                    "Re-evaluate carefully; do not rubber-stamp the prior outcome.\n"
                )

            prompt = f"""You are a neutral content-moderation appeals judge. A creator \
is appealing a platform enforcement action. Your ONLY job is to decide, independently \
of the platform, whether the content actually violates the SPECIFIC policy the platform \
cited - not whether you personally like the content.
{prior}
PLATFORM: {platform}
ENFORCEMENT ACTION APPEALED: {action_type}
POLICY CLAUSE THE PLATFORM CITED (as the creator reports it):
\"\"\"{policy_quote}\"\"\"

CREATOR'S STATEMENT:
\"\"\"{creator_statement}\"\"\"

FULL POLICY PAGE CONTENT (read it to understand the actual rule and its scope):
{policy_page[:5000]}

THE CONTENT THAT WAS ACTIONED (read it and judge against the policy):
{content_page[:5000]}

JUDGING PRINCIPLES:
- Judge ONLY against the cited policy, narrowly. Do not invent other rules.
- The burden is on the enforcement: if the content does not clearly fall under the \
cited policy, the action should be OVERTURNED.
- Distinguish "I dislike this" from "this breaks the stated rule". Edgy, controversial, \
or unpopular content is NOT a violation unless it breaks the cited clause.
- If the cited policy is genuinely broken, rule UPHELD.
- If only part of the content breaks it, or the action is disproportionate (e.g. full \
removal where a lighter action fits), rule PARTIAL.
- If either page is unreachable or the evidence is too weak to prove a violation, lean \
toward OVERTURNED (benefit of the doubt to the creator).

Respond with ONLY a JSON object, no markdown, no extra text:
{{
  "ruling": "<UPHELD | OVERTURNED | PARTIAL>",
  "confidence": <integer 0..100, how certain you are>,
  "rationale": "<2-5 sentence justification citing the specific policy language and \
what in the content does or does not match it>"
}}"""

            res = gl.nondet.exec_prompt(prompt, response_format="json")
            if isinstance(res, str):
                cleaned = res.replace("```json", "").replace("```", "").strip()
                data = json.loads(cleaned)
            else:
                data = res

            ruling = _normalize_ruling(data.get("ruling", ""))
            if not ruling:
                # Unparseable / invalid ruling → benefit of the doubt (product rule)
                ruling = RULING_OVERTURNED
            try:
                conf = _clamp_conf(int(data.get("confidence", 0)))
            except Exception:
                conf = 0
            rationale = str(data.get("rationale", ""))[:2000]

            return json.dumps(
                {"ruling": ruling, "confidence": conf, "rationale": rationale},
                sort_keys=True,
            )

        return gl.eq_principle.prompt_comparative(leader_fn, EQUIVALENCE_PRINCIPLE)

    # === 1. File appeal + deposit fee ===

    @gl.public.write.payable
    def file_appeal(
        self,
        platform: str,
        action_type: str,
        content_url: str,
        policy_url: str,
        policy_quote: str,
        creator_statement: str,
    ) -> int:
        fee = bigint(gl.message.value)
        self._require(fee > bigint(0), "An appeal fee deposit is required")
        self._require(len(content_url.strip()) > 0, "Content URL is required")
        self._require(len(policy_url.strip()) > 0, "Cited policy URL is required")
        self._require(
            action_type in VALID_ACTIONS,
            "action_type must be one of REMOVAL/DEMONETIZATION/STRIKE/AGE_RESTRICT",
        )

        appeal_id = int(self.next_id)
        self.next_id = self.next_id + bigint(1)
        key = str(appeal_id)

        ap = Appeal()
        ap.creator = gl.message.sender_address
        ap.platform = platform.strip()
        ap.action_type = action_type
        ap.content_url = content_url.strip()
        ap.policy_url = policy_url.strip()
        ap.policy_quote = policy_quote
        ap.creator_statement = creator_statement
        ap.fee = fee
        ap.status = APPEAL_FILED
        ap.ruling = ""
        ap.confidence = bigint(0)
        ap.rationale = ""
        ap.fee_refunded = False
        ap.appeal_round = bigint(0)
        ap.previous_ruling = ""
        ap.appealed = False

        self.appeals[key] = ap
        return appeal_id

    # === 2. AI Jury adjudication (initial or after re-trial filing) ===

    @gl.public.write
    def adjudicate(self, appeal_id: int) -> None:
        ap = self._get_appeal(appeal_id)
        self._require(ap.status == APPEAL_FILED, "Appeal is not awaiting review")

        platform = ap.platform
        action_type = ap.action_type
        content_url = ap.content_url
        policy_url = ap.policy_url
        policy_quote = ap.policy_quote
        creator_statement = ap.creator_statement
        appeal_round = int(ap.appeal_round)
        previous_ruling = ap.previous_ruling

        ap.status = APPEAL_REVIEWING

        raw = self._run_jury(
            platform,
            action_type,
            content_url,
            policy_url,
            policy_quote,
            creator_statement,
            appeal_round,
            previous_ruling,
        )

        try:
            if isinstance(raw, (bytes, bytearray)):
                raw = raw.decode("utf-8")
            verdict = json.loads(raw) if isinstance(raw, str) else raw
        except Exception:
            self._err("AI Jury returned unreadable payload")

        ruling = _normalize_ruling(verdict.get("ruling", ""))
        self._require(ruling in VALID_RULINGS, "Invalid ruling produced")
        try:
            confidence = _clamp_conf(int(verdict.get("confidence", 0)))
        except Exception:
            confidence = 0
        rationale = str(verdict.get("rationale", ""))[:2000]

        ap.ruling = ruling
        ap.confidence = bigint(confidence)
        ap.rationale = rationale
        ap.status = APPEAL_RESOLVED

        # Reputation is counted on each finalizable verdict (including re-trial).
        # For re-trials, count only the latest outcome (previous already counted
        # on first resolve — skip double-count by only counting round 0 here, and
        # re-count delta on round 1 by adjusting overturned if outcome flipped).
        if appeal_round == 0:
            self._bump_platform_stats(platform, ruling)
        else:
            # Re-trial: if outcome class flipped, adjust overturned counter.
            prev = previous_ruling
            prev_win = _creator_wins(prev)
            now_win = _creator_wins(ruling)
            if prev_win != now_win:
                name = (platform or "unknown").strip() or "unknown"
                ov = (
                    self.platform_overturned[name]
                    if name in self.platform_overturned
                    else bigint(0)
                )
                if now_win and not prev_win:
                    self.platform_overturned[name] = ov + bigint(1)
                elif prev_win and not now_win and ov > bigint(0):
                    self.platform_overturned[name] = ov - bigint(1)

    # === 3. One-round re-trial (loser or any interested party posts a bond) ===

    @gl.public.write.payable
    def request_retrial(self, appeal_id: int) -> None:
        """
        After RESOLVED and before fee settlement, post a bond to re-run the AI Jury
        once. Bond is added to the appeal fee pot (settled with the original fee).
        """
        ap = self._get_appeal(appeal_id)
        self._require(ap.status == APPEAL_RESOLVED, "Only a resolved appeal can be retried")
        self._require(not ap.appealed, "Re-trial already used for this appeal")
        self._require(int(ap.appeal_round) < MAX_APPEALS, "Max re-trial rounds reached")
        self._require(not ap.fee_refunded, "Fee already settled")

        bond = bigint(gl.message.value)
        self._require(bond > bigint(0), "Re-trial bond required")

        ap.previous_ruling = ap.ruling
        ap.appeal_round = ap.appeal_round + bigint(1)
        ap.appealed = True
        ap.fee = ap.fee + bond
        ap.ruling = ""
        ap.confidence = bigint(0)
        ap.rationale = ""
        ap.status = APPEAL_FILED  # back to queue for adjudicate()

    # === 4. Settle fee based on ruling (pull-payment for refunds) ===

    @gl.public.write
    def settle_fee(self, appeal_id: int) -> None:
        ap = self._get_appeal(appeal_id)
        self._require(ap.status == APPEAL_RESOLVED, "Appeal has no resolved ruling")
        self._require(not ap.fee_refunded, "Fee already settled")

        ap.fee_refunded = True
        amount = bigint(ap.fee)
        ap.fee = bigint(0)

        # Creator wins (OVERTURNED or PARTIAL) -> credit withdrawable.
        # UPHELD -> treasury (operational cost / spam filter).
        if _creator_wins(ap.ruling):
            self._credit(ap.creator, amount)
        else:
            self.treasury = self.treasury + amount

        ap.status = APPEAL_CLOSED

    # === 5. Pull-payment withdraw ===

    @gl.public.write
    def withdraw(self) -> None:
        """Anyone with a credited refund pulls their balance in one tx."""
        key = _addr_hex(gl.message.sender_address)
        bal = self.withdrawable[key] if key in self.withdrawable else bigint(0)
        self._require(bal > bigint(0), "Nothing to withdraw")
        self.withdrawable[key] = bigint(0)
        gl.get_contract_at(gl.message.sender_address).emit_transfer(value=u256(bal))

    @gl.public.write
    def withdraw_treasury(self, to: str, amount: int) -> None:
        self._require(
            gl.message.sender_address == self.owner,
            "Only the contract owner can withdraw treasury",
        )
        self._require(amount > 0, "Amount must be positive")
        amt = bigint(amount)
        self._require(amt <= self.treasury, "Amount exceeds treasury balance")
        self.treasury = self.treasury - amt
        gl.get_contract_at(_to_address(to)).emit_transfer(value=u256(amt))

    # === Read-only views ===

    @gl.public.view
    def get_appeal(self, appeal_id: int) -> str:
        ap = self._get_appeal(appeal_id)
        return json.dumps({
            "creator": _addr_hex(ap.creator),
            "platform": ap.platform,
            "action_type": ap.action_type,
            "content_url": ap.content_url,
            "policy_url": ap.policy_url,
            "policy_quote": ap.policy_quote,
            "creator_statement": ap.creator_statement,
            "fee": int(ap.fee),
            "status": ap.status,
            "ruling": ap.ruling,
            "confidence": int(ap.confidence),
            "rationale": ap.rationale,
            "fee_refunded": ap.fee_refunded,
            "appeal_round": int(ap.appeal_round),
            "previous_ruling": ap.previous_ruling,
            "appealed": ap.appealed,
        })

    @gl.public.view
    def get_total_appeals(self) -> int:
        return int(self.next_id)

    @gl.public.view
    def get_treasury(self) -> int:
        return int(self.treasury)

    @gl.public.view
    def get_withdrawable(self, who: str) -> int:
        key = who if who.startswith("0x") else ("0x" + who)
        # Also try lowercase/as-stored; callers pass hex from wallet.
        if key in self.withdrawable:
            return int(self.withdrawable[key])
        # Try matching without normalizing further.
        if who in self.withdrawable:
            return int(self.withdrawable[who])
        return 0

    @gl.public.view
    def get_platform_stats(self, platform: str) -> str:
        name = (platform or "").strip() or "unknown"
        total = int(self.platform_total[name]) if name in self.platform_total else 0
        ov = (
            int(self.platform_overturned[name])
            if name in self.platform_overturned
            else 0
        )
        rate = int((ov * 100) / total) if total > 0 else 0
        return json.dumps({
            "platform": name,
            "total_resolved": total,
            "creator_favorable": ov,
            "overturn_rate_pct": rate,
        })
