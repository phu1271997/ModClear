# GenLayer Intelligent Contract - Developer Troubleshooting Guide

If you are developing or extending this contract using an AI coding assistant (like Claude, Gemini, or GPT), feed this document to the LLM context first. This ensures the assistant adheres to GenLayer's strict runtime constraints and avoids introducing compilation/consensus bugs.

---

## 1. Storage Type Constraints (bigint vs u256)

### The Issue:
Standard integer types (`int`) and the `u256` type (from `genlayer.py.types`) **cannot** be used as storage types inside class-level mappings or storage structs. Doing so causes metadata validation errors inside the GenVM simulator:
`TypeError: use bigint or one of sized integers please`

### The Rule:
- Always use `bigint` for storage fields and values that persist inside mapping structures (e.g., `TreeMap`, `Appeal` structs).
- Only convert/cast to `u256` or `int` temporarily in memory when interacting with external APIs (like sending token value transfers).

```python
# BAD
class Appeal(Record):
    fee: u256
    confidence: int

# GOOD
from genlayer.std import bigint
class Appeal(Record):
    fee: bigint
    confidence: bigint
```

---

## 2. Native Token Transfers

### The Issue:
The legacy/Ethereum-like API `gl.eth.send_value(...)` **does not exist** in the GenLayer Python SDK. Using it results in:
`AttributeError: module 'genlayer.gl' has no attribute 'eth'`

### The Rule:
To send native tokens (GEN) to any address, retrieve a contract proxy for that address and call `emit_transfer`:
```python
# BAD
gl.eth.send_value(recipient_address, u256(amount))

# GOOD
gl.get_contract_at(recipient_address).emit_transfer(value=u256(amount))
```

---

## 3. Client Transaction Calls in `gltest`

### The Issue:
Dynamic write-method proxies in `gltest` (Python SDK) do not accept transaction metadata (like `value` or `account`) as keyword arguments directly on the method invocation.
```python
# BAD (Raises TypeError)
contract.file_appeal(args=[...], value=5000, account=creator)
```

### The Rule:
Use the fluent client interface API sequence: `.connect(account)`, followed by the `.method(args)`, and finally `.transact(value=X)`:
```python
# GOOD
contract.connect(creator).file_appeal(
    args=["YouTube", "DEMONETIZATION", "https://...", "https://...", "quote", "statement"]
).transact(value=5000)
```

---

## 4. Non-Deterministic consensus & Mocking (LLM & Web)

### The Issue:
Functions decorated with `gl.vm.run_nondet_unsafe` execute on the consensus leader. During tests, if the leader attempts real internet calls (`gl.nondet.web.render`) or LLM API requests (`gl.nondet.exec_prompt`) without environment credentials (e.g., `OPENAI_API_KEY`), the transaction fails consensus, leading to confusing state errors like `"Appeal is not awaiting review"`.

### The Rule:
Always install mocks before executing non-deterministic test transactions.

#### RPC JSON-RPC Parameter Formatting:
When invoking the `sim_installMocks` method on the provider, the parameters dictionary **must not** be wrapped in an outer list. If wrapped in a list, GenLayer's internal parameter normalizer converts it into an integer-indexed dictionary, registering `0` mocks.

```python
# BAD (0 mocks registered)
client.provider.make_request(
    method="sim_installMocks",
    params=[{ "llm_mocks": { ... } }]
)

# GOOD (Mocks successfully registered)
client.provider.make_request(
    method="sim_installMocks",
    params={
        "llm_mocks": {
            ".*": json.dumps({
                "ruling": "OVERTURNED",
                "confidence": 85,
                "rationale": "Justification..."
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
```

#### Validator Return Type:
When validating the leader result in `validator_fn`, the argument passed by the simulator engine is wrapped in a `gl.vm.Return` object. You must extract the underlying data through the `.calldata` property:
```python
def validator_fn(leader_res: typing.Any) -> bool:
    if not isinstance(leader_res, gl.vm.Return):
        return False
    leader_data = leader_res.calldata
    # Now parse leader_data (which could be a JSON string or parsed dict/type)
```
