---
description: "Use when writing, running, or debugging tests. Covers the eval suite structure, cawdp_contract test patterns, and failure diagnosis."
applyTo: ["evals/**", "agents/**", "cawdp_contract/tests/**"]
---

# Testing & Evals

## Eval Suite Structure (AgentOS)

The eval surface is two files:

| File | Purpose |
|------|---------|
| `evals/cases.py` | Declares `Case` dataclass instances — one per test |
| `evals/__main__.py` | Runner — wraps agno's `AgentAsJudgeEval` + `ReliabilityEval` |

## cawdp_contract Test Suite

The contract API has 154 unit tests and 14 integration tests.

### Running tests

```bash
# Unit tests only (default — skips integration tests)
python -m pytest cawdp_contract/tests/ -v

# Integration tests (requires live SurrealDB)
SURREALDB_URL=ws://localhost:8099 python -m pytest cawdp_contract/tests/ -v -m integration

# Specific test files
python -m pytest cawdp_contract/tests/test_event_logging.py -v
python -m pytest cawdp_contract/tests/test_utils.py -v
python -m pytest cawdp_contract/tests/test_milestone_5.py -v
```

### Test structure

| File | Tests | Purpose |
|------|-------|---------|
| `test_milestone_1.py` | Schema, config, health | M1 deliverables |
| `test_milestone_2.py` | Workflow creation, triage, design shape | M2 deliverables |
| `test_milestone_3.py` | Contract CRUD, section updates, field catalogue | M3 deliverables |
| `test_milestone_4.py` | Output specs, submit/approve, Stage 1 gate | M4 deliverables |
| `test_milestone_5.py` | Progress, next-action, history, hide_locked | M5 deliverables |
| `test_event_logging.py` | Event CRUD, router integration | Audit trail |
| `test_utils.py` | normalize() unit tests | SurrealDB type conversion |
| `conftest.py` | Shared fixtures, MockDB, sample data | Test infrastructure |

### Mock DB pattern

Tests use `MockDB` classes that route `query()` calls by SQL verb:

```python
class MockDB:
    def query(self, query: str, params: dict | None = None) -> list[dict]:
        q = query.strip()
        if "INSERT INTO contract_event" in q:
            # Handle event logging
        if "contract_event" in q:
            return []  # Return empty for SELECT on events (triggers fallback)
        if q.startswith("UPDATE") or q.startswith("INSERT"):
            return [self._single_record]
        if "type::record" in q:
            return [self._single_record]
        return self._list_records
```

### Dependency overrides

Each router has a local `get_db()` function. Override them in tests:

```python
from cawdp_contract.tests.conftest import override_all_dbs, clear_overrides, MockDB

mock = MockDB(single_record=contract_data)
override_all_dbs(mock)
# ... run tests ...
clear_overrides()
```

### Integration tests

Integration tests require a live SurrealDB instance with the schema deployed:

```bash
# Deploy schema first
python scripts/run_migration.py

# Then run integration tests
SURREALDB_URL=ws://localhost:8099 python -m pytest cawdp_contract/tests/ -v -m integration
```

## Case Shape

```python
@dataclass(frozen=True)
class Case:
    name: str
    agent: Agent
    input: str

    # Judge (LLM rubric, binary pass/fail): set to enable.
    criteria: str | None = None

    # Reliability (tool-call assertion): set to enable.
    expected_tool_calls: tuple[str, ...] | None = None
    allow_additional_tool_calls: bool = True
```

Each case runs the agent once. If both `criteria` and `expected_tool_calls` are set, both checks run against the same response — one agent call, two checks.

## Running Evals

```bash
python -m evals                # full suite (concise)
python -m evals -v             # stream agent runs with rich panels
python -m evals --case <name>  # single case
```

Exit 0 on all-pass, non-zero on any failure or error.

## Preconditions

- Postgres reachable on 5432 (`nc -z localhost 5432`). If not, `docker compose up -d agentos-db`.
- Venv active (`source .venv/bin/activate`). If missing, `./scripts/venv_setup.sh`.
- `.env` populated with `OPENAI_API_KEY`. The runner auto-loads `.env` via `evals.dotenv.load_dotenv()`.
- No AgentOS server needs to be running — evals import agents directly.

## WebSearch Tool Name Gotcha

`evals/cases.py` pins `_WEB_SEARCH_TOOL` at import time based on `PARALLEL_API_KEY`:

```python
_WEB_SEARCH_TOOL = "parallel_search" if getenv("PARALLEL_API_KEY") else "web_search"
```

If your shell has the var set but `.env` doesn't (or vice versa), the assertion checks the wrong tool. Sync them before debugging.

## Diagnosing Failures

| Symptom | Likely cause | Fix |
|---|---|---|
| Judge fails, "answer is right but missing X" | Agent instructions don't push for X | Tighten `INSTRUCTIONS` in `agents/<slug>.py` |
| Judge fails, response is fabricated | Agent hallucinated | Add "if you can't find a real source, say so" rule |
| Reliability fails: "missing tool X" | Agent didn't call expected tool | Strengthen routing in instructions, or broaden `expected_tool_calls` |
| Reliability fails: "additional tool Y called" | Agent fanned out | Tighten instructions or set `allow_additional_tool_calls=True` |
| Same case flips PASS/FAIL across runs | Judge variance — rubric too loose | Tighten `criteria` (more specific, more falsifiable) |
| Many cases fail at once | Broad regression (model swap, MCP down) | Diagnose root cause first |

**Rule:** never weaken a case to make it green. Edit a case only when the assertion was wrong (overspecified rubric, wrong tool name).

## Adding a New Case

Add to `evals/cases.py`:

```python
Case(
    name="<short_id>",
    agent=<the_agent>,
    input="<prompt>",
    criteria="<rubric describing a correct response>",
    expected_tool_calls=("<tool_name>",),
)
```

Run `python -m evals --case <name>` to confirm it passes.

## Eval History

Every case logs to Postgres via `db=eval_db`. Connect your AgentOS at os.agno.com to view eval history over time — useful for catching slow drift.
