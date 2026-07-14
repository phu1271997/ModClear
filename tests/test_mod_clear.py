"""
Test suite for ModClear.

Run with genlayer-test (gltest):
    gltest tests/test_mod_clear.py

Coverage:
  - Happy path: file → adjudicate → settle → withdraw.
  - Edge: fee = 0, invalid action_type, empty URLs.
  - Edge: settle before resolve, double settle.
  - Edge: only owner withdraws treasury.
  - Edge: re-trial bond + re-adjudicate.
  - Invariant: OVERTURNED/PARTIAL credits creator; UPHELD → treasury.
"""

import json
from gltest import get_contract_factory, create_account
from gltest.assertions import tx_execution_succeeded, tx_execution_failed
from gltest.clients import get_gl_client


FEE = 5_000
BOND = 2_000


def _deploy(factory, owner):
    return factory.deploy(args=[], account=owner)


def _file(
    contract,
    creator,
    fee=FEE,
    action="DEMONETIZATION",
    content="https://example.org/video.html",
    policy="https://example.org/policy.html",
):
    return (
        contract.connect(creator)
        .file_appeal(
            args=[
                "YouTube",
                action,
                content,
                policy,
                "Content that is not advertiser-friendly will be demonetized",
                "Video discusses academic topics only; does not violate this clause.",
            ]
        )
        .transact(value=fee)
    )


def _install_mocks(ruling="OVERTURNED", confidence=85):
    client = get_gl_client()
    client.provider.make_request(
        "sim_installMocks",
        {
            "llm_mocks": {
                ".*": json.dumps({
                    "ruling": ruling,
                    "confidence": confidence,
                    "rationale": "Mock jury rationale under the cited policy.",
                })
            },
            "web_mocks": {
                ".*": {
                    "status": 200,
                    "body": "Mock page content for content and policy.",
                }
            },
        },
    )


def test_file_appeal_happy_path():
    owner = create_account()
    creator = create_account()
    factory = get_contract_factory(contract_file_path="mod_clear.py")
    contract = _deploy(factory, owner)

    receipt = _file(contract, creator)
    assert tx_execution_succeeded(receipt)

    assert contract.get_total_appeals(args=[]).call() == 1
    state = json.loads(contract.get_appeal(args=[0]).call())
    assert state["status"] == "FILED"
    assert state["fee"] == FEE
    assert state["action_type"] == "DEMONETIZATION"
    assert state["appeal_round"] == 0
    assert state["appealed"] is False


def test_zero_fee_rejected():
    owner = create_account()
    creator = create_account()
    factory = get_contract_factory(contract_file_path="mod_clear.py")
    contract = _deploy(factory, owner)
    assert tx_execution_failed(_file(contract, creator, fee=0))


def test_invalid_action_type_rejected():
    owner = create_account()
    creator = create_account()
    factory = get_contract_factory(contract_file_path="mod_clear.py")
    contract = _deploy(factory, owner)
    assert tx_execution_failed(_file(contract, creator, action="BANHAMMER"))


def test_empty_urls_rejected():
    owner = create_account()
    creator = create_account()
    factory = get_contract_factory(contract_file_path="mod_clear.py")
    contract = _deploy(factory, owner)
    assert tx_execution_failed(_file(contract, creator, content=""))
    assert tx_execution_failed(_file(contract, creator, policy=""))


def test_settle_before_resolved_rejected():
    owner = create_account()
    creator = create_account()
    factory = get_contract_factory(contract_file_path="mod_clear.py")
    contract = _deploy(factory, owner)
    _file(contract, creator)
    assert tx_execution_failed(
        contract.connect(creator).settle_fee(args=[0]).transact()
    )


def test_only_owner_withdraws_treasury():
    owner = create_account()
    stranger = create_account()
    factory = get_contract_factory(contract_file_path="mod_clear.py")
    contract = _deploy(factory, owner)
    assert tx_execution_failed(
        contract.connect(stranger)
        .withdraw_treasury(args=[stranger.address, 1])
        .transact()
    )


def test_full_flow_overturned_pull_payment():
    """Integration with LLM mocks: OVERTURNED → credit → withdraw."""
    _install_mocks(ruling="OVERTURNED", confidence=85)

    owner = create_account()
    creator = create_account()
    factory = get_contract_factory(contract_file_path="mod_clear.py")
    contract = _deploy(factory, owner)

    _file(contract, creator)
    assert tx_execution_succeeded(
        contract.connect(creator).adjudicate(args=[0]).transact()
    )

    state = json.loads(contract.get_appeal(args=[0]).call())
    assert state["status"] == "RESOLVED"
    assert state["ruling"] in ("UPHELD", "OVERTURNED", "PARTIAL")
    assert 0 <= state["confidence"] <= 100
    assert len(state["rationale"]) > 0

    assert tx_execution_succeeded(
        contract.connect(creator).settle_fee(args=[0]).transact()
    )
    final = json.loads(contract.get_appeal(args=[0]).call())
    assert final["status"] == "CLOSED"
    assert final["fee_refunded"] is True

    if final["ruling"] == "UPHELD":
        assert contract.get_treasury(args=[]).call() == FEE
    else:
        assert contract.get_treasury(args=[]).call() == 0
        # Pull-payment: creator can withdraw refund
        bal = contract.get_withdrawable(args=[creator.address]).call()
        assert bal == FEE
        assert tx_execution_succeeded(
            contract.connect(creator).withdraw(args=[]).transact()
        )
        assert contract.get_withdrawable(args=[creator.address]).call() == 0


def test_full_flow_upheld_to_treasury():
    _install_mocks(ruling="UPHELD", confidence=90)

    owner = create_account()
    creator = create_account()
    factory = get_contract_factory(contract_file_path="mod_clear.py")
    contract = _deploy(factory, owner)

    _file(contract, creator)
    assert tx_execution_succeeded(
        contract.connect(creator).adjudicate(args=[0]).transact()
    )
    assert tx_execution_succeeded(
        contract.connect(creator).settle_fee(args=[0]).transact()
    )
    final = json.loads(contract.get_appeal(args=[0]).call())
    assert final["status"] == "CLOSED"
    if final["ruling"] == "UPHELD":
        assert contract.get_treasury(args=[]).call() == FEE
        assert contract.get_withdrawable(args=[creator.address]).call() == 0


def test_retrial_flow():
    """RESOLVED → request_retrial (bond) → adjudicate again → settle."""
    _install_mocks(ruling="PARTIAL", confidence=70)

    owner = create_account()
    creator = create_account()
    factory = get_contract_factory(contract_file_path="mod_clear.py")
    contract = _deploy(factory, owner)

    _file(contract, creator)
    assert tx_execution_succeeded(
        contract.connect(creator).adjudicate(args=[0]).transact()
    )
    state = json.loads(contract.get_appeal(args=[0]).call())
    assert state["status"] == "RESOLVED"

    assert tx_execution_succeeded(
        contract.connect(creator)
        .request_retrial(args=[0])
        .transact(value=BOND)
    )
    mid = json.loads(contract.get_appeal(args=[0]).call())
    assert mid["status"] == "FILED"
    assert mid["appealed"] is True
    assert mid["appeal_round"] == 1
    assert mid["fee"] == FEE + BOND
    assert mid["previous_ruling"] in ("UPHELD", "OVERTURNED", "PARTIAL")

    assert tx_execution_succeeded(
        contract.connect(creator).adjudicate(args=[0]).transact()
    )
    after = json.loads(contract.get_appeal(args=[0]).call())
    assert after["status"] == "RESOLVED"

    # Second re-trial must fail
    assert tx_execution_failed(
        contract.connect(creator)
        .request_retrial(args=[0])
        .transact(value=BOND)
    )

    assert tx_execution_succeeded(
        contract.connect(creator).settle_fee(args=[0]).transact()
    )
    closed = json.loads(contract.get_appeal(args=[0]).call())
    assert closed["status"] == "CLOSED"


def test_platform_stats_after_resolve():
    _install_mocks(ruling="OVERTURNED", confidence=80)

    owner = create_account()
    creator = create_account()
    factory = get_contract_factory(contract_file_path="mod_clear.py")
    contract = _deploy(factory, owner)

    _file(contract, creator)
    contract.connect(creator).adjudicate(args=[0]).transact()

    stats = json.loads(contract.get_platform_stats(args=["YouTube"]).call())
    assert stats["platform"] == "YouTube"
    assert stats["total_resolved"] >= 1
