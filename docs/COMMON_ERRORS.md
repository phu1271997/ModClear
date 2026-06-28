# ⚠️ GENLAYER STUDIO — COMMON DEPLOYMENT ERRORS CHEATSHEET

Before writing or modifying any GenLayer Intelligent Contract (`.py`), you MUST follow these 7 rules. These are battle-tested lessons from real deployment failures on `https://studio.genlayer.com/run-debug`.

## 🛡️ THE 7 RULES (NON-NEGOTIABLE)

### 1️⃣ FIRST LINE must be `# v0.2.16`
```python
# v0.2.16
# { "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }
from genlayer import *
```
**Without this:** Studio falls back to v0.1.0 → errors:
- `Contract Queues not found`
- `Contract IdlenessPhase not found`
- `Contract RevealingPhase not found`

### 2️⃣ NEVER reassign `TreeMap()` or `DynArray()` in `__init__`
```python
# ❌ WRONG — causes AssertionError: Is right the same storage type? TreeMap <- TreeMap
def __init__(self):
    self.projects = TreeMap()
    self.balances = TreeMap()

# ✅ CORRECT — GenVM auto-initializes TreeMap/DynArray to empty
def __init__(self):
    self.total_supply = u256(0)
    self.token_symbol = "TOKEN"
    # TreeMap fields are already {} — do NOT touch them here
```

### 3️⃣ NO `float` in public method signatures
```python
# ❌ WRONG — schema parser rejects float
@gl.public.write
def submit(self, amount: float): ...

# ✅ CORRECT — use int (multiply by 100 for cents if needed)
@gl.public.write
def submit(self, amount: int): ...
```

### 4️⃣ Allowed public method types ONLY
✅ `str`, `bool`, `bytes`, `int`, sized ints (`u8`..`u256`, `i8`..`i256`), `Address`, `DynArray[T]`, `TreeMap[K, V]`
❌ `float`, `list[T]`, `dict[K,V]`, non-instantiated generics, custom classes

### 5️⃣ Storage uses `TreeMap`/`DynArray`, NEVER `dict`/`list`
```python
class Contract(gl.Contract):
    # ✅ CORRECT
    users: TreeMap[str, u256]
    posts: DynArray[str]
    
    # ❌ WRONG
    users: dict[str, int]
    posts: list[str]
```

### 6️⃣ Class MUST be named `Contract` and extend `gl.Contract`
```python
# ✅ CORRECT
class Contract(gl.Contract):
    ...

# ❌ WRONG — Studio cannot find entry point
class MyAwesomeContract(gl.Contract):
    ...
```

### 7️⃣ ALL `gl.nondet.*` calls MUST be inside `gl.vm.run_nondet_unsafe(leader_fn, validator_fn)`
```python
# ❌ WRONG — direct call in deterministic code
@gl.public.write
def verify(self):
    result = gl.nondet.exec_prompt("...")  # CRASH

# ✅ CORRECT — wrapped in run_nondet_unsafe
@gl.public.write
def verify(self):
    def leader_fn():
        return gl.nondet.exec_prompt("...", response_format="json")
    def validator_fn(leader_result) -> bool:
        return isinstance(leader_result, gl.vm.Return)
    return gl.vm.run_nondet_unsafe(leader_fn, validator_fn)
```

---

## 🩺 DEPLOYMENT TROUBLESHOOTING

### Symptom: Studio shows `Contract Queues not found`
→ Check Rule #1 (missing `# v0.2.16`)

### Symptom: Transaction FINALIZED but Result: ERROR with `AssertionError: TreeMap <- TreeMap`
→ Check Rule #2 (TreeMap reassigned in `__init__`)

### Symptom: Contract won't compile, schema error
→ Check Rules #3, #4, #5 (forbidden types)

### Symptom: Sidebar shows "Not deployed yet" but tx is FINALIZED
→ Click tx in sidebar → inspect "Result" field. If ERROR, read the traceback.

### Symptom: Deploy worked yesterday but fails today
→ Studio → Settings → **Reset Storage** → Confirm → Hard refresh (Cmd+Shift+R)

---

## ✅ PRE-DEPLOY CHECKLIST

Before saving any `.py` contract, verify:
- [ ] Line 1 is exactly `# v0.2.16`
- [ ] Line 2 is the `# { "Depends": "py-genlayer:..." }` comment
- [ ] `__init__` has NO `TreeMap()` or `DynArray()` assignments
- [ ] No `float` anywhere in public method signatures
- [ ] All storage fields use `TreeMap[K,V]` or `DynArray[T]` (never `dict`/`list`)
- [ ] Main class is named exactly `Contract` extending `gl.Contract`
- [ ] All `gl.nondet.web.render` / `gl.nondet.exec_prompt` calls wrapped in `gl.vm.run_nondet_unsafe`

---

## 🚀 RECOMMENDED DEPLOY PROCEDURE

1. Open `https://studio.genlayer.com/run-debug`
2. **Settings → Reset Storage → Confirm**
3. **Hard refresh** (Cmd+Shift+R / Ctrl+Shift+F5)
4. Deploy `storage_test.py` FIRST (minimal sanity contract) — verify environment works
5. If storage_test succeeds → deploy main contract
6. After deploy, **click the transaction** in sidebar to verify `Result: SUCCESS` (not just `Status: FINALIZED`)
7. If `Result: ERROR` → read traceback, map to one of the 7 rules above


**R13 — NEVER do explicit alias imports for genlayer:**
Always use ONLY `from genlayer import *` to import the SDK. Never use `import genlayer as gl` or `import genlayer`. The GenVM sandbox runtime automatically injects a custom, fully-configured global `gl` object when `from genlayer import *` is executed. Re-importing genlayer manually overrides this sandbox-injected `gl` object with a standard empty module, causing tracebacks like `AttributeError: module 'genlayer' has no attribute 'Contract'`.
