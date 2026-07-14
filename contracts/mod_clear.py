# v0.2.16
# { "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }
from genlayer import *

import json
from dataclasses import dataclass


# =============================================================================
# ModClear - Decentralized Content Moderation Appeals Court
#
# Creators file appeals against platform enforcement (removal / demonetization /
# strike). An on-chain AI jury renders the content URL and the cited policy URL,
# then rules UPHELD / OVERTURNED / PARTIAL with confidence and rationale.
#
# Lint / GenVM rules applied here:
#   R1  file starts with # v0.2.16 + Depends py-genlayer
#   R2  no TreeMap/DynArray assignment in __init__
#   R14 storage numbers are bigint
#   R19 TreeMap keys are str (never bigint / int)
#   custom storage structs use @allow_storage + @dataclass
#   nondet only inside eq_principle.prompt_comparative
#
# Why GenLayer: subjective judgment over live unstructured web data is the
# product core; Solidity cannot do this.
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

# Validators agree on outcome CLASS for the creator, not JSON bytes.
# WIN = OVERTURNED or PARTIAL. LOSE = UPHELD. Rationale wording may differ.
EQUIVALENCE_PRINCIPLE = (
    "Both answers must reach the SAME substantive outcome for the creator. "
    "Treat OVERTURNED and PARTIAL as creator-favorable (WIN). Treat UPHELD as "
    "platform-favorable (LOSE). The two answers are equivalent only if both are "
    "WIN or both are LOSE. Confidence may differ by at most 30 points. "
    "Rationale wording may differ; the decision class must not."
)

MAX_RETRIALS = 1


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


def _normalize_ruling(raw) -> str:
    r = str(raw or "").strip().upper()
    if r in VALID_RULINGS:
        return r
    return ""


def _creator_wins(ruling: str) -> bool:
    return ruling in (RULING_OVERTURNED, RULING_PARTIAL)


@allow_storage
@dataclass
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
    appeal_round: bigint
    previous_ruling: str
    appealed: bool


class Contract(gl.Contract):
    # R19: TreeMap keys MUST be str.
    appeals: TreeMap[str, Appeal]
    next_id: bigint
    owner: Address
    treasury: bigint
    # address hex -> refund credit (pull-payment)
    withdrawable: TreeMap[str, bigint]
    platform_total: TreeMap[str, bigint]
    platform_overturned: TreeMap[str, bigint]

    def __init__(self):
        # R2: do NOT touch TreeMap fields here.
        self.next_id = bigint(0)
        self.owner = gl.message.sender_address
        self.treasury = bigint(0)

    def _require(self, cond: bool, msg: str) -> None:
        if not cond:
            raise gl.vm.UserError(msg)

    def _get_appeal(self, appeal_id: int) -> Appeal:
        key = str(int(appeal_id))
        if key not in self.appeals:
            raise gl.vm.UserError("Appeal not found")
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
                    "\nTHIS IS RE-TRIAL ROUND "
                    + str(appeal_round)
                    + ". Previous on-chain ruling was "
                    + previous_ruling
                    + ". Re-evaluate carefully; do not rubber-stamp the prior outcome.\n"
                )

            prompt = (
                "You are a neutral content-moderation appeals judge. A creator "
                "is appealing a platform enforcement action. Decide independently "
                "whether the content actually violates the SPECIFIC policy the "
                "platform cited - not whether you personally like the content.\n"
                + prior
                + "\nPLATFORM: "
                + platform
                + "\nENFORCEMENT ACTION APPEALED: "
                + action_type
                + "\nPOLICY CLAUSE THE PLATFORM CITED:\n\"\"\""
                + policy_quote
                + "\"\"\"\n\nCREATOR STATEMENT:\n\"\"\""
                + creator_statement
                + "\"\"\"\n\nFULL POLICY PAGE:\n"
                + policy_page[:5000]
                + "\n\nCONTENT ACTIONED:\n"
                + content_page[:5000]
                + "\n\nJUDGING PRINCIPLES:\n"
                "- Judge ONLY against the cited policy, narrowly.\n"
                "- Burden is on enforcement: if content does not clearly fall "
                "under the cited policy, rule OVERTURNED.\n"
                "- Edgy or unpopular is not a violation unless the clause is broken.\n"
                "- Clear violation -> UPHELD.\n"
                "- Partial match or disproportionate action -> PARTIAL.\n"
                "- Unreachable pages or weak evidence -> lean OVERTURNED.\n\n"
                "Respond with ONLY JSON, no markdown:\n"
                '{"ruling":"<UPHELD|OVERTURNED|PARTIAL>",'
                '"confidence":<0-100>,'
                '"rationale":"<2-5 sentences>"}'
            )

            res = gl.nondet.exec_prompt(prompt, response_format="json")
            if isinstance(res, str):
                cleaned = res.replace("```json", "").replace("```", "").strip()
                data = json.loads(cleaned)
            else:
                data = res

            ruling = _normalize_ruling(data.get("ruling", ""))
            if not ruling:
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

    # --- Write methods (review path: file -> adjudicate -> get -> settle) ---

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

        self.appeals[key] = Appeal(
            creator=gl.message.sender_address,
            platform=platform.strip(),
            action_type=action_type,
            content_url=content_url.strip(),
            policy_url=policy_url.strip(),
            policy_quote=policy_quote,
            creator_statement=creator_statement,
            fee=fee,
            status=APPEAL_FILED,
            ruling="",
            confidence=bigint(0),
            rationale="",
            fee_refunded=False,
            appeal_round=bigint(0),
            previous_ruling="",
            appealed=False,
        )
        return appeal_id

    @gl.public.write
    def adjudicate(self, appeal_id: int) -> None:
        ap = self._get_appeal(appeal_id)
        self._require(ap.status == APPEAL_FILED, "Appeal is not awaiting review")

        # Capture locals for nondet block (cannot touch storage inside).
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
            raise gl.vm.UserError("AI Jury returned unreadable payload")

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

        if appeal_round == 0:
            self._bump_platform_stats(platform, ruling)
        else:
            prev_win = _creator_wins(previous_ruling)
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

    @gl.public.write.payable
    def request_retrial(self, appeal_id: int) -> None:
        ap = self._get_appeal(appeal_id)
        self._require(ap.status == APPEAL_RESOLVED, "Only a resolved appeal can be retried")
        self._require(not ap.appealed, "Re-trial already used for this appeal")
        self._require(int(ap.appeal_round) < MAX_RETRIALS, "Max re-trial rounds reached")
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
        ap.status = APPEAL_FILED

    @gl.public.write
    def settle_fee(self, appeal_id: int) -> None:
        ap = self._get_appeal(appeal_id)
        self._require(ap.status == APPEAL_RESOLVED, "Appeal has no resolved ruling")
        self._require(not ap.fee_refunded, "Fee already settled")

        ap.fee_refunded = True
        amount = bigint(ap.fee)
        ap.fee = bigint(0)

        if _creator_wins(ap.ruling):
            self._credit(ap.creator, amount)
        else:
            self.treasury = self.treasury + amount

        ap.status = APPEAL_CLOSED

    @gl.public.write
    def withdraw(self) -> None:
        key = _addr_hex(gl.message.sender_address)
        bal = self.withdrawable[key] if key in self.withdrawable else bigint(0)
        self._require(bal > bigint(0), "Nothing to withdraw")
        self.withdrawable[key] = bigint(0)
        gl.get_contract_at(gl.message.sender_address).emit_transfer(value=u256(int(bal)))

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
        gl.get_contract_at(_to_address(to)).emit_transfer(value=u256(int(amt)))

    # --- Views ---

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
            "fee_refunded": bool(ap.fee_refunded),
            "appeal_round": int(ap.appeal_round),
            "previous_ruling": ap.previous_ruling,
            "appealed": bool(ap.appealed),
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
        if key in self.withdrawable:
            return int(self.withdrawable[key])
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
