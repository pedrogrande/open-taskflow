---
name: agno-context-management
description: 'Design and control the context sent to Agno agents and teams — system messages, instructions, context providers, session state, dependencies, few-shot examples, dynamic instructions, prompt caching, context scoping, chat history, and agentic features. Use when an agent drifts from its purpose, when context is too large or too sparse, when adding external data sources via context providers, when scoping what an agent reads and writes, when optimizing token costs through prompt caching, when managing chat history or tool call history, when configuring agentic memory or knowledge filters, or when deciding between context providers vs direct tools vs knowledge.'
argument-hint: 'Context issue and target, e.g. "scope context for design-writer agent" or "add database context provider"'
user-invocable: true
---

# Agno Context Management

Context engineering is the process of designing and controlling the information sent to language models. In Agno, this means crafting the system message, attaching context providers, managing session state, and scoping what each agent reads and writes. The principle: **less context, better work** — every token competes for the model's finite attention budget.

## When to Use

- An agent drifts from its stated purpose (too much or wrong context)
- Adding external data sources (Slack, database, filesystem, web) to an agent
- Scoping what an agent can read and write (context isolation)
- Reducing token costs through prompt caching
- Injecting dynamic data (session state, dependencies, user identity)
- Adding few-shot examples to guide output format
- Building a custom context provider for a domain-specific data source
- Deciding between direct tools vs context providers vs knowledge
- Managing chat history length or filtering tool calls from history
- Configuring agentic memory, agentic state, or agentic knowledge filters
- Propagating user/session context through context provider sub-agents

## Context Architecture

An Agno agent's context has four layers:

```
System message (always sent)
├── Description + role
├── Instructions (static or dynamic)
├── Additional context + expected output
├── Memories, session state, datetime, location
└── Tool instructions (from Toolkits / Context Providers)

User message (per request)
├── The user's input
├── Knowledge references (if add_knowledge_to_context=True)
└── Dependencies (if add_dependencies_to_context=True)

Chat history (configurable)
├── Last N runs (num_history_runs)
└── Session summary (if add_session_summary_to_context=True)

Additional input (optional)
└── Few-shot examples (additional_input)
```

## Procedure

### 1. Scope the Context Window

Before writing instructions, answer three questions:

- **What does this agent need to read?** Named files only, not categories.
- **What does this agent write?** One artefact, one location.
- **What is this agent explicitly forbidden from reading?** If it can reach it, it might load it.

This produces a scoped context window — not a timeline of everything the agent could possibly need.

### 2. Write Minimal Instructions

Write instructions like a linter config, not a job description:

**Bad** — prose that the model pattern-matches against:
```
You are a Test Writer Agent. Your role is to translate acceptance criteria
into executable tests. You should carefully read the task acceptance criteria
provided to you and produce a comprehensive test suite...
```

**Good** — structured, minimal, unambiguous:
```
READS: task-ac.md only
WRITES: .framework/features/[slug]/tasks/[task-slug]/tests.md
FORMAT: Given/When/Then, one test per AC condition
NEVER: read feature-spec.md or parent AC
```

**Rules:**
- Critical rules at the top of the file
- Boundaries at the bottom
- Nothing important in the middle (lost-in-the-middle problem)
- Use `add_instruction_tags=True` for models that benefit from XML structure

### 3. Configure the System Message

The system message is built from agent parameters. Key parameters:

| Parameter | Type | Default | Effect |
|-----------|------|---------|--------|
| `description` | `str` | `None` | Added at the start of system message |
| `instructions` | `List[str]` or callable | `None` | Task-specific instructions (static or dynamic) |
| `additional_context` | `str` | `None` | Appended to end of system message |
| `expected_output` | `str` | `None` | Describes desired output format |
| `add_instruction_tags` | `bool` | `True` | Wrap instructions in `<instructions>` tags |
| `system_message` | `str` | `None` | Override the entire system message (ignores all other settings) |
| `build_context` | `bool` | `True` | Disable context building entirely |
| `add_history_to_context` | `bool` | `False` | Adds chat history to context |
| `num_history_runs` | `int` | `None` | Number of history runs (requires `add_history_to_context`) |
| `max_tool_calls_from_history` | `int` | `None` | Max tool calls to keep from history (v2.2.1+) |
| `enable_agentic_memory` | `bool` | `False` | Adds `update_user_memory` tool |
| `enable_agentic_state` | `bool` | `False` | Adds `update_session_state` tool |
| `enable_agentic_knowledge_filters` | `bool` | `False` | Lets agent choose knowledge filters |

> **Full parameter reference**: See [references/parameters.md](references/parameters.md) for all 22 system message parameters, construction order, and the complete troubleshooting table.

**System message order** (static content first for prompt caching):

```
1. Description → 2. Role → 3. Instructions → 4. Additional information → 5. Expected output → 6. Additional context → 7. Memories → 8. Session summary → 9. Session state
```

**Toolkit instructions** — Toolkits with `instructions` and `add_instructions=True` inject their instructions after `<additional_information>` tags.

### 4. Dynamic Instructions

Instructions can be a function that receives `RunContext` or `Agent`:

```python
from agno.run import RunContext

def get_instructions(run_context: RunContext):
    user = run_context.session_state.get("current_user_id", "the user")
    return [f"Make the story about {user}."]

agent = Agent(instructions=get_instructions)
```

Or access the agent object:

```python
def get_instructions(agent: Agent) -> List[str]:
    return [f"Your name is {agent.name}!", "Talk in haikus."]
```

Dynamic instructions are resolved at runtime, before each run.

### 5. Context Providers

Context providers solve three problems: tool sprawl, name collisions, and system-prompt bloat. Each provider wraps an external system and exposes it as one or two namespaced tools.

**Built-in providers** (see [references/parameters.md](references/parameters.md) for full catalog):

| Provider | Import | Read | Write |
|----------|--------|------|-------|
| `FilesystemContextProvider` | `agno.context.fs` | Yes | No |
| `DatabaseContextProvider` | `agno.context.database` | Yes | Yes |
| `WebContextProvider` | `agno.context.web` | Yes | No |
| `SlackContextProvider` | `agno.context.slack` | Yes | Yes |
| `GmailContextProvider` | `agno.context.gmail` | Yes | Yes |
| `MCPContextProvider` | `agno.context.mcp` | Yes | No |
| `WikiContextProvider` | `agno.context.wiki` | Yes | Yes |
| `WorkspaceContextProvider` | `agno.context.workspace` | Yes | No |

**Usage:**

```python
from agno.context.fs import FilesystemContextProvider
from agno.context.database import DatabaseContextProvider

fs = FilesystemContextProvider(id="docs", root="./documentation")
db = DatabaseContextProvider(sql_engine=engine, readonly_engine=readonly_engine)

agent = Agent(
    tools=[*fs.get_tools(), *db.get_tools()],
    instructions="\n".join([fs.instructions(), db.instructions()]),
)
# Agent sees: query_docs, query_database, update_database
```

> **The `id` parameter determines tool names**: `id="docs"` → `query_docs` / `update_docs`. Choose short, descriptive IDs.

**RunContext propagation** — When a provider runs a sub-agent, it forwards `user_id`, `session_id`, `metadata`, and `dependencies` from the calling agent. This ensures per-user auth tokens and session isolation work across provider boundaries. Message history and `session_state` stay with the outer agent.

**Context modes:**

| Mode | Tools exposed | When to use |
|------|--------------|-------------|
| `default` | `query_<id>` + `update_<id>` | Most cases — read/write separation |
| `agent` | `query_<id>` only | Read-only, maximum abstraction |
| `tools` | Raw toolkit methods | Fine-grained control, source-specific agents |

```python
from agno.context.mode import ContextMode

slack = SlackContextProvider(mode=ContextMode.agent)  # query_slack only
```

**Sub-agent model** — use a cheaper model for the provider's internal work:

```python
slack = SlackContextProvider(model=OpenAIResponses(id="gpt-5.4-mini"))
agent = Agent(model=OpenAIResponses(id="gpt-5.4"), tools=slack.get_tools())
```

**Read/write control:**

```python
gmail = GmailContextProvider(write=False)   # Read-only: query_gmail only
gmail = GmailContextProvider(read=False)     # Write-only: update_gmail only
```

**Async lifecycle** — some providers need setup/teardown:

```python
mcp = MCPContextProvider(server_name="github", transport="stdio", command="npx", args=[...])
await mcp.asetup()
try:
    agent = Agent(tools=mcp.get_tools())
    await agent.arun("List my recent PRs")
finally:
    await mcp.aclose()
```

### 6. Custom Context Providers

Subclass `ContextProvider` for domain-specific data sources:

```python
from agno.context import Answer, ContextProvider, Status

class FAQContextProvider(ContextProvider):
    def status(self) -> Status:
        return Status(ok=True, detail=f"{len(FAQ)} entries")

    async def astatus(self) -> Status:
        return self.status()

    def query(self, question: str, *, run_context=None) -> Answer:
        key = next((k for k in FAQ if k in question.lower()), None)
        return Answer(text=FAQ[key] if key else "No FAQ entry matches.")

    async def aquery(self, question: str, *, run_context=None) -> Answer:
        return self.query(question, run_context=run_context)

faq = FAQContextProvider(id="faq")
agent = Agent(tools=faq.get_tools())  # Agent sees: query_faq
```

**Required methods:** `query()`, `aquery()`, `status()`, `astatus()`

**Optional methods for write support:** `update()`, `aupdate()`, `_default_tools()`

**Answer with source documents:**

```python
return Answer(
    text="Found 3 matching policies.",
    results=[
        Document(id="doc1", name="Refund Policy", uri="/policies/refund.md", snippet="..."),
    ]
)
```

**Custom instructions:**

```python
def instructions(self) -> str:
    return "Use query_jira for finding issues by key, assignee, or labels."
```

### 7. Session State

Session state persists across runs within a session. Requires `db=` on the agent.

```python
from agno.run import RunContext

def add_item(run_context: RunContext, item: str) -> str:
    """Add an item to the shopping list."""
    run_context.session_state["shopping_list"].append(item)
    return f"Added '{item}'"

agent = Agent(
    db=get_surrealdb(),
    session_state={"shopping_list": []},
    tools=[add_item],
    instructions="Current shopping list: {shopping_list}",
    add_session_state_to_context=True,
)
```

**Key patterns:**
- Set default state via `session_state={"key": value}`
- Access in tools via `run_context.session_state`
- Reference in instructions via `{key}` template syntax
- Persist by setting `db=` on the agent
- Auto-update by setting `enable_agentic_state=True`
- Share across team members (team-level session state)

**Agentic state** — let the agent manage its own state:

```python
agent = Agent(
    session_state={"shopping_list": []},
    add_session_state_to_context=True,  # Required
    enable_agentic_state=True,           # Adds update_session_state tool
)
```

### 7a. Chat History

Control how much conversation history the agent sees:

```python
agent = Agent(
    db=get_surrealdb(),
    add_history_to_context=True,
    num_history_runs=5,  # Last 5 runs
)
```

**Filter tool calls from history** (v2.2.1+) — limit tool call clutter:

```python
agent = Agent(
    db=get_surrealdb(),
    add_history_to_context=True,
    num_history_runs=10,
    max_tool_calls_from_history=3,  # Keep only last 3 tool calls
)
```

`max_tool_calls_from_history` filters tool calls from the runs loaded by `num_history_runs`. The database always contains the complete history.

### 7b. Agentic Features

Three agentic features add self-management tools to the agent:

| Feature | Parameter | Tool Added |
|---------|-----------|------------|
| Agentic Memory | `enable_agentic_memory=True` | `update_user_memory` |
| Agentic State | `enable_agentic_state=True` | `update_session_state` |
| Agentic Knowledge Filters | `enable_agentic_knowledge_filters=True` | (modifies `search_knowledge_base`) |

All three require their corresponding `add_*_to_context=True` flag. See [references/parameters.md](references/parameters.md) for details.

### 8. Dependencies

Inject variables into agent context with template substitution:

```python
agent = Agent(
    dependencies={"name": "John Doe", "timezone": "UTC"},
    instructions="The current user is {name}. Their timezone is {timezone}.",
    add_dependencies_to_context=True,
)
```

Values can be callables — resolved at runtime:

```python
def get_current_time():
    from datetime import datetime
    return datetime.now().isoformat()

agent = Agent(
    dependencies={"current_time": get_current_time},
    instructions="Current time: {current_time}",
)
```

### 9. Few-Shot Examples

Add example interactions via `additional_input`:

```python
from agno.models.message import Message

support_examples = [
    Message(role="user", content="I forgot my password"),
    Message(role="assistant", content="I'll help you reset your password..."),
    Message(role="user", content="I've been charged twice!"),
    Message(role="assistant", content="I apologize for the billing error..."),
]

agent = Agent(
    additional_input=support_examples,
    instructions=["You are a customer support specialist."],
)
```

### 10. Context Caching

Most model providers cache repetitive content. Agno places static content at the start of the system message to maximize cache hits.

**Optimization strategies:**
- Put static content (description, core instructions) at the top
- Put dynamic content (session state, datetime) at the bottom
- Use `system_message` to manually control order for fine-tuning
- Process tasks sequentially with the same agent to warm the cache

**Provider-specific caching:**
- OpenAI: automatic prompt caching (prefix matching)
- Anthropic: explicit cache control markers
- OpenRouter: prefix-based caching

### 11. Context vs Tools vs Knowledge

| Need | Use | Why |
|------|-----|-----|
| Query Slack, Drive, DB | Context Provider | Avoids tool sprawl, namespaced tools |
| Call specific APIs | Direct Tools | Fine-grained control over actions |
| Search documents | Knowledge Base | Semantic search, chunking, embeddings |
| User-specific data | Dependencies | Template substitution, runtime resolution |
| Track state across runs | Session State | Persisted in DB, shared in teams |
| Output format examples | Few-shot (`additional_input`) | Pattern learning without prose |

## Common Patterns for This Project

### Current Context Usage
- **`WorkspaceContextProvider`**: `agents/code_search.py` — wraps filesystem behind `query_my_codebase` tool
- **`MCPTools`**: `agents/web_search.py` — direct tools for web search
- **Session state**: `cawdp_pipeline/tools/decision_tools.py` — `run_context.session_state` for in-workflow state
- **Dependencies**: Not yet used — opportunity for user identity injection

### Pattern: Context Provider for Codebase Access
```python
from agno.context.workspace import WorkspaceContextProvider

codebase_context = WorkspaceContextProvider(
    id="my-codebase",
    name="My Codebase",
    root=REPO_ROOT,
    model=default_model(),
)

agent = Agent(
    tools=codebase_context.get_tools(),
    instructions=INSTRUCTIONS + "\n\n" + codebase_context.instructions(),
)
```

### Pattern: Session State in Workflow Tools
```python
def _load_register(self, run_context: RunContext | None = None) -> DecisionRegister:
    if run_context and run_context.session_state:
        cached = run_context.session_state.get("decisions")
        if cached is not None:
            return DecisionRegister(decisions=cached)
    return self._load_from_file()
```

### Pattern: Minimal Instructions (Context Engineering Approach)
```python
DESIGN_WRITER_INSTRUCTIONS = """\
READS: catalogue entry + any existing design spec
WRITES: D-{output_id}.md in specs/design/P{phase:02d}/
FORMAT: Markdown with sections per catalogue depth
NEVER: read implementation specs or decision register directly
"""
```

## Troubleshooting

Common issues and fixes — see [references/parameters.md](references/parameters.md) for the full troubleshooting table.

| Symptom | Cause | Fix |
|---------|-------|-----|
| Agent ignores instructions | Too much context, instructions buried in middle | Move critical rules to top, trim prose |
| Agent hallucinates tool names | >20 tools on one agent | Use Context Providers to namespace tools |
| Session state not persisting | Missing `db=` on agent | Add `db=get_surrealdb()` |
| `enable_agentic_state` not working | Missing `add_session_state_to_context` | Set both `add_session_state_to_context=True` and `enable_agentic_state=True` |
| `enable_agentic_memory` not working | Missing `add_memories_to_context` | Set both `add_memories_to_context=True` and `enable_agentic_memory=True` |
| Tool calls flooding context | Too many tool results in history | Set `max_tool_calls_from_history=N` |

## Related Resources

- [Agno context engineering overview](https://docs.agno.com/context/overview) — design principles
- [Agno agent context](https://docs.agno.com/context/agent/overview) — system message parameters
- [Agno team context](https://docs.agno.com/context/team/overview) — team leader system message
- [Agno context providers overview](https://docs.agno.com/context-providers/overview) — what they solve
- [Agno using providers](https://docs.agno.com/context-providers/using-providers) — attaching, modes, lifecycle
- [Agno custom providers](https://docs.agno.com/context-providers/custom-providers) — building your own
- [Agno provider catalog](https://docs.agno.com/context-providers/providers/overview) — all built-in providers
- [Agno session state](https://docs.agno.com/state/agent/overview) — state management
- [Agno dependencies](https://docs.agno.com/dependencies/overview) — dependency injection
- [Agno few-shot learning](https://docs.agno.com/context/agent/few-shot-learning) — additional_input
- Project: `agents/code_search.py` — WorkspaceContextProvider pattern
- Project: `cawdp_pipeline/tools/decision_tools.py` — session state in tools
- Project: `docs/context-engineering-approach.md` — context scoping methodology