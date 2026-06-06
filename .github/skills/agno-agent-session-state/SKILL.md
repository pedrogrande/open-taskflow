---
name: agno-agent-session-state
description: 'Agno agent session state patterns for this project — add_session_state_to_context=True for {variable} interpolation in instructions (also interpolates toolkit instructions and @tool docstrings), assert session_state is not None before .update(), Agent.db= must be SurrealDb wrapper not raw surrealdb-py connection, pre-hook functions must read session_state via agent.session_state not as a parameter, and pipeline agents must set add_history_to_context=False to prevent history hallucination. Use when configuring agent session state, writing pre-hooks, setting db= on pipeline agents, or hitting AttributeError on get_session(), mypy errors on session_state, or agents that skip tool calls on iteration 2+.'
argument-hint: 'What you are configuring, e.g. "pre-hook" or "session state interpolation" or "Agent.db="'
user-invocable: true
---

# Agno Agent Session State Patterns

Six hard-won patterns from the CAWDP pipeline. They all concern how agents interact
with session state and the `db=` argument.

## When to Use

- An agent `instructions` string with `{output_id}` renders as the literal `{output_id}`
- Hitting `AttributeError: 'BlockingWsSurrealConnection' object has no attribute 'get_session'`
- mypy strict error: `Item "None" of "dict[str, Any] | None" has no attribute "update"`
- `TypeError: _my_hook() missing 1 required positional argument: 'session_state'`
- Writing `pre_hooks` functions for pipeline agents
- Agent makes 24 tool calls on iteration 1, then exactly 1 call on every subsequent iteration (history hallucination)
- `{placeholder}` in a `Toolkit._INSTRUCTIONS` or `@tool` docstring is unexpectedly replaced or left as a literal filled by the LLM

---

## Rule 1 — `add_session_state_to_context=True` for `{variable}` interpolation (L-008, L-029)

The `{variable}` template syntax in `instructions` **only works** when `add_session_state_to_context=True` is set. Without it, the template renders as the literal string.

```python
# ❌ WRONG — {output_id} rendered as literal text
agent = Agent(
    session_state={"output_id": "", "depth": ""},
    instructions="Current output: {output_id}",
)

# ✅ CORRECT
agent = Agent(
    session_state={"output_id": "", "depth": ""},
    add_session_state_to_context=True,           # ← required
    instructions="Current output: {output_id}",  # ← now interpolated
)
```

### ⚠️ Interpolation scope is ALL assembled context — not just `instructions` (L-029)

`add_session_state_to_context=True` causes Agno to interpolate `{key}` in **every string it passes to the LLM**, including:

- The agent's `instructions` field (expected)
- `Toolkit._INSTRUCTIONS` strings (not obvious)
- **Every `@tool` method docstring** (easy to miss — affects all registered tools)
- Context provider output strings

If a `{key}` is not in `session_state`, the placeholder is left as a literal — and the LLM fills it with its own Agno run UUID or fabricates a value. This produces silent wrong data in tools like `write_verdict(review_run_id="{run_id}")` where the LLM invents the ID.

```python
# ❌ DANGEROUS — {run_id} in docstring gets interpolated (or left literal → LLM invents)
class DesignReviewToolkit(Toolkit):
    _INSTRUCTIONS = "Use write_verdict with run_id format '{run_id}:{iteration}'."

    def write_verdict(self, review_run_id: str) -> str:
        """Write verdict. review_run_id must be '{run_id}:{iteration}'."""

# ✅ SAFE — plain prose, no placeholders
class DesignReviewToolkit(Toolkit):
    _INSTRUCTIONS = (
        "Use write_verdict with the exact review_run_id from session state. "
        "Do NOT append a suffix or use your Agno run UUID."
    )

    def write_verdict(self, review_run_id: str) -> str:
        """Write a section verdict. review_run_id is provided in session state."""
```

**Rule**: Avoid `{placeholder}` patterns in any `Toolkit` or `@tool` docstring when `add_session_state_to_context=True`. Use plain prose and reinforce correct values in the agent's own `instructions`.

---

## Rule 2 — `agent.session_state` is `dict | None` — assert before `.update()` (L-015)

Agno types `Agent.session_state` as `dict[str, Any] | None`. Pipeline agents always
initialise it with a dict, so `None` is never reached at runtime — but mypy strict
mode catches the potential `None` and refuses `.update()`.

```python
# ❌ mypy strict error: Item "None" of "dict[str, Any] | None" has no attribute "update"
design_writer.session_state.update({"output_id": output_id})

# ✅ CORRECT — assert satisfies mypy; always true for pipeline agents
assert design_writer.session_state is not None
design_writer.session_state.update({"output_id": output_id})
```

Always initialise `session_state` in the `Agent()` constructor to avoid `None`:

```python
agent = Agent(
    session_state={"output_id": "", "depth": "shallow"},
    ...
)
```

---

## Rule 3 — `Agent.db=` and `Workflow.db=` must be `SurrealDb` wrapper (L-018)

`db=` expects Agno's `SurrealDb` storage wrapper, which provides `get_session()`,
`upsert_session()`, etc. Passing a raw `surrealdb-py` connection crashes at runtime:

```python
# ❌ WRONG — raw connection crashes: AttributeError: 'BlockingWsSurrealConnection'
#             object has no attribute 'get_session'
from cawdp_development.db._connection import _connect
agent = Agent(db=_connect(), ...)

# ✅ CORRECT — Agno SurrealDb wrapper
from db import get_surrealdb
agent = Agent(
    db=get_surrealdb(table_name="cawdp_design_writer_sessions"),
    ...
)
workflow = Workflow(
    db=get_surrealdb(table_name="cawdp_design_spec_workflow"),
    ...
)
```

**Boundary rule**:

- `_connect()` → use inside toolkit CRUD functions (`upsert_section`, `read_catalogue_entry`, etc.)
- `get_surrealdb(table_name=...)` → use for `db=` on `Agent` and `Workflow` objects

The two connections point at the same SurrealDB instance but serve different layers:
`_connect()` is a raw WebSocket connection; `get_surrealdb()` is Agno's session storage wrapper.

---

## Rule 4 — Pre-hooks: read `agent.session_state`, don't declare it as a parameter (L-019)

Agno's `execute_pre_hooks` injects these named parameters only:
`run_input`, `run_context`, `agent`, `session`, `user_id`, `debug_mode`, `metadata`.

`session_state` is **not** in this list. Declaring it as a parameter causes a runtime crash:

```python
# ❌ WRONG — TypeError: _inject_failing_sections() missing 1 required positional argument: 'session_state'
def _inject_failing_sections(
    agent: Agent,
    session_state: dict[str, Any] | None,  # not injected
) -> None:
    ...

# ✅ CORRECT — read agent.session_state inside the function body
def _inject_failing_sections(agent: Agent) -> None:
    ss = agent.session_state
    if not ss:
        return
    output_id: str = ss.get("output_id", "")
    failing: list[str] = ss.get("failing_sections", [])
    agent.instructions = agent.instructions + f"\n\nRevise only: {failing}"
```

Valid injectable parameter names (verified): `agent`, `run_input`, `run_context`,
`session`, `user_id`, `debug_mode`, `metadata`.

---

## Rule 5 — Pipeline agents must set `add_history_to_context=False` (L-028)

Pipeline agents (spec writers, reviewers) run inside a `Loop`. Each iteration starts
a new call to `agent.run()`. By default `add_history_to_context=True`, so the agent
sees its full message history from **all prior iterations** as chat history.

**Symptom:** Iteration 1 makes 24+ tool calls and produces a complete spec. Iterations
2–N each make exactly **1 LLM call** and return something like:
> "I have already written all the sections for this spec. No further work is needed."

The agent treats its prior iteration's output as proof of completion and halts.

```python
# ❌ WRONG — default add_history_to_context=True causes hallucinated "already done"
design_writer = Agent(
    id="design-writer",
    ...
)

# ✅ CORRECT — each iteration is stateless (context comes from session_state and tools)
design_writer = Agent(
    id="design-writer",
    add_history_to_context=False,  # ← prevent prior-iteration messages leaking in
    num_history_runs=0,            # ← belt-and-suspenders
    ...
)
```

**Diagnostic signal:** Check iteration 1 vs iteration 2 tool call count. If iteration 1
has N calls and iterations 2+ have exactly 1, this is the history hallucination pattern.

Only disable history when the agent is driven entirely by session_state, tools, and a
fresh `pre_hook` injection (e.g., failing sections list). If an agent legitimately needs
prior-turn context (chat agents, multi-turn interactive agents), keep `add_history_to_context=True`.
