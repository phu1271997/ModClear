# Changelog

Follows [Semantic Versioning](https://semver.org/).

## [1.1.0] — Builder resubmission quality pass

### Changed
- **Consensus:** replaced custom `run_nondet_unsafe` validator (which could soft-pass on LLM failure) with `gl.eq_principle.prompt_comparative` on outcome class (creator WIN vs LOSE).
- **Refunds:** push-on-settle replaced with **pull-payment** (`withdrawable` map + `withdraw()`).
- **Storage keys:** appeals keyed by `str(id)` for TreeMap safety across GenVM builds.
- Errors prefer `gl.vm.UserError` when available.

### Added
- **One-round re-trial:** `request_retrial(appeal_id)` payable bond before settle; re-runs jury.
- **Platform reputation:** `get_platform_stats(platform)` (total resolved, creator-favorable, rate %).
- Views: `get_withdrawable(who)`.
- Frontend: full flow UI (re-trial, withdraw, platform stats, live counters), **demo scenario buttons**, public `frontend/samples/*` pages for end-to-end demos.
- Tests: re-trial once, pull-payment, UPHELD→treasury, platform stats.
- README: live URL, API table, scoring-oriented architecture notes.

### Fixed
- Removed accidental junk directory from brace-expansion (`{contracts,frontend...`).
- Validator no longer returns `True` when independent LLM fails (eliminated “schema-only soft pass”).

## [1.0.0] — Initial release

### Added
- Intelligent Contract `mod_clear.py`: FILED → REVIEWING → RESOLVED → CLOSED.
- AI Jury via web.render + exec_prompt; rulings UPHELD / OVERTURNED / PARTIAL.
- Anti-spam fee; frontend single-file dApp; tests; storage_test; docs.
