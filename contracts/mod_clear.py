# v0.2.16
# { "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }
from genlayer import *

import json
import typing


# =============================================================================
# ModClear - Decentralized Content Moderation Appeals Court
#
# Problem: Creators get their content removed, demonetized, or struck by platforms
# (YouTube, TikTok, etc.) - often incorrectly. The appeal process of platforms is a
# black box: slow, obscure, and biased towards the platform itself. Creators lose
# revenue without a neutral court to review the decision independently.
#
# Solution: Turn every appeal into an on-chain AI Jury verdict.
#
# 1. Creators file an appeal, providing content URL, policy URL, policy quote,
#    and creator statement. They deposit an appeal fee (anti-spam, refunded on win).
# 2. AI Jury (validators running LLMs) read the content and policy on-chain, and
#    judge independently: does the content actually violate the cited policy?
#    Produces RULING: UPHELD, OVERTURNED, or PARTIAL.
# 3. The verdict, confidence, and rationale are recorded on-chain, public and immutable.
# 4. If OVERTURNED/PARTIAL, the fee is refunded to the creator. If UPHELD, the fee
#    goes to the treasury (operational cost).
#
# Why GenLayer: Deciding if content violates a natural language policy is subjective
# and requires reading unstructured web data + reasoning. Traditional smart contracts
# cannot do this. AI is the core of the product.
# =============================================================================


# Appeal States
APPEAL_FILED = "FILED"           # Filed + fee deposited, awaiting adjudication
APPEAL_REVIEWING = "REVIEWING"  # Sent to AI Jury
APPEAL_RESOLVED = "RESOLVED"    # Verdict produced
APPEAL_CLOSED = "CLOSED"        # Fee settled (refunded or collected)

# Ruling types
RULING_UPHELD = "UPHELD"            # Platform was right, keep enforcement
RULING_OVERTURNED = "OVERTURNED"   # Creator vindicated, content does not violate policy
RULING_PARTIAL = "PARTIAL"         # Partial violation or excessive enforcement


@allow_storage
class Appeal:
    creator: Address
    platform: str                  # Platform name (e.g. YouTube, TikTok)
    action_type: str               # REMOVAL | DEMONETIZATION | STRIKE | AGE_RESTRICT
    content_url: str               # URL of the actioned content
    policy_url: str                # URL of the cited policy guidelines
    policy_quote: str              # Section of policy creator claims was misapplied
    creator_statement: str         # Creator's argument / justification
    fee: bigint                    # Deposited fee amount

    status: str
    ruling: str                    # UPHELD | OVERTURNED | PARTIAL
    confidence: bigint             # 0..100, consensus confidence level
    rationale: str                 # AI rationale explaining the decision
    fee_refunded: bool


class Contract(gl.Contract):
    # Storage. DO NOT initialize TreeMap/DynArray in __init__ (Rule #2).
    appeals: TreeMap[bigint, Appeal]
    next_id: bigint
    owner: Address
    treasury: bigint                 # Fees collected from failed appeals

    def __init__(self):
        self.next_id = bigint(0)
        self.owner = gl.message.sender_address
        self.treasury = bigint(0)

    # === Helpers ===

    def _require(self, cond: bool, msg: str) -> None:
        if not cond:
            raise Exception(msg)

    def _get_appeal(self, appeal_id: bigint) -> Appeal:
        if appeal_id not in self.appeals:
            raise Exception("Appeal not found")
        return self.appeals[appeal_id]

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
    ) -> bigint:
        fee = bigint(gl.message.value)
        self._require(fee > bigint(0), "An appeal fee deposit is required")
        self._require(len(content_url) > 0, "Content URL is required")
        self._require(len(policy_url) > 0, "Cited policy URL is required")

        valid_actions = ["REMOVAL", "DEMONETIZATION", "STRIKE", "AGE_RESTRICT"]
        self._require(
            action_type in valid_actions,
            "action_type must be one of REMOVAL/DEMONETIZATION/STRIKE/AGE_RESTRICT",
        )

        appeal_id = self.next_id
        self.next_id = appeal_id + bigint(1)

        ap = Appeal()
        ap.creator = gl.message.sender_address
        ap.platform = platform
        ap.action_type = action_type
        ap.content_url = content_url
        ap.policy_url = policy_url
        ap.policy_quote = policy_quote
        ap.creator_statement = creator_statement
        ap.fee = fee
        ap.status = APPEAL_FILED
        ap.ruling = ""
        ap.confidence = 0
        ap.rationale = ""
        ap.fee_refunded = False

        self.appeals[appeal_id] = ap
        return appeal_id

    # === 2. AI Jury Adjudication ===

    @gl.public.write
    def adjudicate(self, appeal_id: bigint) -> None:
        ap = self._get_appeal(appeal_id)
        self._require(ap.status == APPEAL_FILED, "Appeal is not awaiting review")

        # Extract local variables (nondet block cannot access storage)
        platform = ap.platform
        action_type = ap.action_type
        content_url = ap.content_url
        policy_url = ap.policy_url
        policy_quote = ap.policy_quote
        creator_statement = ap.creator_statement

        ap.status = APPEAL_REVIEWING

        def leader_fn() -> typing.Any:
            try:
                content_page = gl.nondet.web.render(content_url, mode="text")
            except Exception:
                content_page = "[UNREACHABLE: could not load the content URL]"
            try:
                policy_page = gl.nondet.web.render(policy_url, mode="text")
            except Exception:
                policy_page = "[UNREACHABLE: could not load the policy URL]"

            prompt = f"""You are a neutral content-moderation appeals judge. A creator \
is appealing a platform enforcement action. Your ONLY job is to decide, independently \
of the platform, whether the content actually violates the SPECIFIC policy the platform \
cited - not whether you personally like the content.

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
            return res

        def validator_fn(leader_res: typing.Any) -> bool:
            # Semantic verification, not just schema (Contract Quality)
            if not isinstance(leader_res, gl.vm.Return):
                return False
            try:
                leader = leader_res.calldata
                if isinstance(leader, (bytes, str)):
                    leader = json.loads(leader)
            except Exception:
                return False

            if not isinstance(leader, dict):
                return False
            if "ruling" not in leader or "confidence" not in leader:
                return False

            leader_ruling = str(leader.get("ruling", "")).upper()
            if leader_ruling not in (RULING_UPHELD, RULING_OVERTURNED, RULING_PARTIAL):
                return False
            try:
                conf = int(leader["confidence"])
            except Exception:
                return False
            if conf < 0 or conf > 100:
                return False

            # Independent validator evaluation: read pages and run own LLM
            try:
                content_page = gl.nondet.web.render(content_url, mode="text")
            except Exception:
                content_page = "[UNREACHABLE]"
            try:
                policy_page = gl.nondet.web.render(policy_url, mode="text")
            except Exception:
                policy_page = "[UNREACHABLE]"

            own_prompt = f"""You independently review a content-moderation appeal. \
Decide if the content violates ONLY the cited policy. Edgy/unpopular content is not a \
violation unless it breaks the cited clause. If evidence is weak or unreachable, lean \
OVERTURNED. Output ONLY JSON: {{"ruling":"<UPHELD|OVERTURNED|PARTIAL>"}}.

PLATFORM: {platform}
ACTION: {action_type}
CITED POLICY CLAUSE:
\"\"\"{policy_quote}\"\"\"
POLICY PAGE:
{policy_page[:5000]}
CONTENT ACTIONED:
{content_page[:5000]}"""
            try:
                own = gl.nondet.exec_prompt(own_prompt, response_format="json")
                if isinstance(own, (bytes, str)):
                    own = json.loads(own)
                own_ruling = str(own["ruling"]).upper()
            except Exception:
                # Fall back to structural validation if LLM call fails
                return True

            if own_ruling not in (RULING_UPHELD, RULING_OVERTURNED, RULING_PARTIAL):
                return True

            # Consensus on meaning: must agree on whether creator wins/loses.
            # PARTIAL is compatible with both sides, but UPHELD vs OVERTURNED is rejected.
            opposite = (
                (leader_ruling == RULING_UPHELD and own_ruling == RULING_OVERTURNED)
                or (leader_ruling == RULING_OVERTURNED and own_ruling == RULING_UPHELD)
            )
            if opposite:
                return False

            return True

        result = gl.vm.run_nondet_unsafe(leader_fn, validator_fn)

        verdict = result
        if isinstance(verdict, (bytes, str)):
            verdict = json.loads(verdict)

        ruling = str(verdict["ruling"]).upper()
        self._require(
            ruling in (RULING_UPHELD, RULING_OVERTURNED, RULING_PARTIAL),
            "Invalid ruling produced",
        )
        confidence = int(verdict.get("confidence", 0))
        if confidence < 0:
            confidence = 0
        if confidence > 100:
            confidence = 100

        ap.ruling = ruling
        ap.confidence = confidence
        ap.rationale = str(verdict.get("rationale", ""))
        ap.status = APPEAL_RESOLVED

    # === 3. Settle Fee based on ruling ===

    @gl.public.write
    def settle_fee(self, appeal_id: bigint) -> None:
        ap = self._get_appeal(appeal_id)
        self._require(ap.status == APPEAL_RESOLVED, "Appeal has no resolved ruling")
        self._require(not ap.fee_refunded, "Fee already settled")

        ap.fee_refunded = True

        # Creator wins (OVERTURNED or PARTIAL) -> refund fee. UPHELD -> treasury.
        if ap.ruling == RULING_OVERTURNED or ap.ruling == RULING_PARTIAL:
            amount = bigint(ap.fee)
            ap.fee = 0
            gl.get_contract_at(ap.creator).emit_transfer(value=u256(amount))
        else:
            self.treasury = self.treasury + bigint(ap.fee)
            ap.fee = 0

        ap.status = APPEAL_CLOSED

    # === Owner: withdraw treasury ===

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
        gl.get_contract_at(Address(to)).emit_transfer(value=u256(amt))

    # === Read-only views ===

    @gl.public.view
    def get_appeal(self, appeal_id: bigint) -> str:
        ap = self._get_appeal(appeal_id)
        return json.dumps({
            "creator": ap.creator.as_hex,
            "platform": ap.platform,
            "action_type": ap.action_type,
            "content_url": ap.content_url,
            "policy_url": ap.policy_url,
            "policy_quote": ap.policy_quote,
            "creator_statement": ap.creator_statement,
            "fee": ap.fee,
            "status": ap.status,
            "ruling": ap.ruling,
            "confidence": ap.confidence,
            "rationale": ap.rationale,
            "fee_refunded": ap.fee_refunded,
        })

    @gl.public.view
    def get_total_appeals(self) -> int:
        return int(self.next_id)

    @gl.public.view
    def get_treasury(self) -> int:
        return int(self.treasury)
