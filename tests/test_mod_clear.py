"""
Test suite cho ModClear.

Chạy với genlayer-test (gltest):
    gltest tests/test_mod_clear.py

Bộ test phủ:
  - Happy path: nộp appeal → adjudicate → settle fee.
  - Edge: fee = 0 bị từ chối.
  - Edge: action_type không hợp lệ bị từ chối.
  - Edge: content_url / policy_url rỗng bị từ chối.
  - Edge: settle_fee khi chưa resolved bị từ chối.
  - Edge: chỉ owner rút treasury.
  - Bất biến: OVERTURNED/PARTIAL hoàn phí creator, UPHELD vào treasury.

Lưu ý: adjudicate() phụ thuộc LLM + web.render → test tích hợp cần môi trường
có inference. Các test deterministic (state machine, phân quyền, validate input)
assert chắc chắn; test adjudicate kiểm bất biến đầu ra.
"""

import json
from gltest import get_contract_factory, create_account
from gltest.assertions import tx_execution_succeeded, tx_execution_failed
from gltest.clients import get_gl_client


FEE = 5_000


def _deploy(factory, owner):
    return factory.deploy(args=[], account=owner)


def _file(contract, creator, fee=FEE, action="DEMONETIZATION",
          content="https://example.org/video.html",
          policy="https://example.org/policy.html"):
    return contract.connect(creator).file_appeal(
        args=[
            "YouTube", action, content, policy,
            "Content that is not advertiser-friendly will be demonetized",
            "Video chỉ thảo luận học thuật, không vi phạm điều khoản này.",
        ]
    ).transact(value=fee)


def test_file_appeal_happy_path():
    owner = create_account(); creator = create_account()
    factory = get_contract_factory(contract_file_path="mod_clear.py")
    contract = _deploy(factory, owner)

    receipt = _file(contract, creator)
    assert tx_execution_succeeded(receipt)

    assert contract.get_total_appeals(args=[]).call() == 1
    state = json.loads(contract.get_appeal(args=[0]).call())
    assert state["status"] == "FILED"
    assert state["fee"] == FEE
    assert state["action_type"] == "DEMONETIZATION"


def test_zero_fee_rejected():
    owner = create_account(); creator = create_account()
    factory = get_contract_factory(contract_file_path="mod_clear.py")
    contract = _deploy(factory, owner)
    assert tx_execution_failed(_file(contract, creator, fee=0))


def test_invalid_action_type_rejected():
    owner = create_account(); creator = create_account()
    factory = get_contract_factory(contract_file_path="mod_clear.py")
    contract = _deploy(factory, owner)
    assert tx_execution_failed(_file(contract, creator, action="BANHAMMER"))


def test_empty_urls_rejected():
    owner = create_account(); creator = create_account()
    factory = get_contract_factory(contract_file_path="mod_clear.py")
    contract = _deploy(factory, owner)
    assert tx_execution_failed(_file(contract, creator, content=""))
    assert tx_execution_failed(_file(contract, creator, policy=""))


def test_settle_before_resolved_rejected():
    owner = create_account(); creator = create_account()
    factory = get_contract_factory(contract_file_path="mod_clear.py")
    contract = _deploy(factory, owner)
    _file(contract, creator)
    # Chưa adjudicate → status FILED → settle_fee phải fail.
    assert tx_execution_failed(contract.connect(creator).settle_fee(args=[0]).transact())


def test_only_owner_withdraws_treasury():
    owner = create_account(); stranger = create_account()
    factory = get_contract_factory(contract_file_path="mod_clear.py")
    contract = _deploy(factory, owner)
    assert tx_execution_failed(
        contract.connect(stranger).withdraw_treasury(args=[stranger.address, 1]).transact()
    )


def test_full_flow_with_adjudication():
    """Tích hợp: cần môi trường LLM. Kiểm bất biến phán quyết + giải quyết phí."""
    client = get_gl_client()
    client.provider.make_request(
        "sim_installMocks",
        {
            "llm_mocks": {
                ".*": json.dumps({
                    "ruling": "OVERTURNED",
                    "confidence": 85,
                    "rationale": "The platform action was incorrect under the cited policy."
                })
            },
            "web_mocks": {
                ".*": {
                    "status": 200,
                    "body": "Mock page content"
                }
            }
        }
    )

    owner = create_account(); creator = create_account()
    factory = get_contract_factory(contract_file_path="mod_clear.py")
    contract = _deploy(factory, owner)

    _file(contract, creator)
    assert tx_execution_succeeded(contract.connect(creator).adjudicate(args=[0]).transact())

    state = json.loads(contract.get_appeal(args=[0]).call())
    assert state["status"] == "RESOLVED"
    assert state["ruling"] in ("UPHELD", "OVERTURNED", "PARTIAL")
    assert 0 <= state["confidence"] <= 100
    assert len(state["rationale"]) > 0

    assert tx_execution_succeeded(contract.connect(creator).settle_fee(args=[0]).transact())
    final = json.loads(contract.get_appeal(args=[0]).call())
    assert final["status"] == "CLOSED"
    assert final["fee_refunded"] is True
    # Bất biến: UPHELD → treasury tăng; ngược lại → treasury không đổi.
    if final["ruling"] == "UPHELD":
        assert contract.get_treasury(args=[]).call() == FEE
    else:
        assert contract.get_treasury(args=[]).call() == 0
