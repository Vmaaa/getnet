# Spec: http-smoke

## Objective
Real-HTTP verification: run all 10 challenge example scenarios against the live compose stack and assert schema + behavior contracts. This module gates the MVP as "done".

## Tech Stack
- stdlib (`urllib`/`json`) + `argparse`; runs via `uv run` from host against `localhost:8000`. No extra dependency.

## Commands
```
uv run python scripts/smoke_http.py --base-url http://localhost:8000
```

## Project Structure
```
scripts/smoke_http.py
```

## Code Style
```python
SCENARIOS = [
    ("What's the difference between the Get Clássica and the Get Smart?", "cliente1988", "knowledge"),
    ("What's the weather forecast in Porto Alegre tomorrow?", "cliente1988", "knowledge"),
    ...
]
```
(The list contains the 10 exact scenario strings from the challenge brief.)

Checks per scenario:
1. HTTP 200 within timeout (120s first call — model warm).
2. Response has `status`, `answer`, `citations`, `tools_used`, `agent_trace`, `session_id`.
3. Knowledge-expected scenarios: `citations` non-empty, `refs` contiguous `1..k`, each citation has `url`, `title`, non-empty `text`.
4. Support-expected scenarios (deposit, card machine connectivity, transaction decline): `tools_used` non-empty and tool names ∈ {get_user_profile, get_transactions, get_device_status}.
5. `agent_trace` entries reference only `knowledge`/`support` agents, attempts ordered.
6. Answer is non-empty English text (heuristic: non-empty, contains ≥3 words).

Report: table `[scenario | status | #citations | tools_used | pass/fail]`, non-zero exit on any failure, `--verbose` prints full JSON.

## Testing Strategy
This module IS a test — it is the integration level. Unit-level coverage lives in the other modules' pytest suites; nothing here needs pytest.

## Boundaries
- Always: run against a freshly booted compose stack (warm `/health` first); fail loudly.
- Ask first: adding assertions that depend on specific LLM answer content (flaky by design).
- Never: mock HTTP in this script; skip failures silently.

## Success Criteria
All 10 scenarios pass against `container-v2` stack; script exits 0; results table committed in the final report/README section.

## Open Questions
None.
