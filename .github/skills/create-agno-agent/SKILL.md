---
name: create-agno-agent
description: 'Create Agno agents using all the latest features from the Agno SDK. Use when building new agents, adding tools, configuring memory, knowledge, context providers, guardrails, structured output, session state, compression, or any Agno Agent feature. Covers the full Agent constructor, registration in AgentOS, and best practices for the agno-surrealdb-railway stack.'
argument-hint: 'Agent name and purpose, e.g. "research-agent — searches the web and summarizes findings"'
user-invocable: true
---

# Create Agno Agent

Build production-grade Agno agents with the latest SDK features, following the patterns used in this project (SurrealDB persistence, AgentOS runtime, Railway deployment).

## When to Use

- Creating a new agent from scratch
- Adding tools, memory, knowledge, or context providers to an existing agent
- Configuring structured output, guardrails, session state, or compression
- Registering an agent or workflow in `app/main.py`
- Debugging agent configuration issues

## Architecture Context

```
AgentOS  (app/main.py)
├── WebSearch  (agents/web_search.py)   — Direct tools pattern
└── CodeSearch (agents/code_search.py)   — ContextProvider pattern
```

- **Model**: `app.settings.default_model()` — single place to bump
- **DB**: `db.get_surrealdb()` for sessions/memory, `db.create_surrealdb_knowledge()` for RAG
- **AgentOS**: `app/main.py` registers all agents, teams, workflows, interfaces

## Procedure

### 1. Choose the Agent Pattern

| Pattern | When | Example |
|---------|------|---------|
| **Direct tools** | Agent calls tools itself | `agents/web_search.py` |
| **Context provider** | Reduce tool surface via sub-agent | `agents/code_search.py` |
| **Knowledge + RAG** | Agent needs domain documents | See Knowledge section |
| **Structured output** | Agent must return typed data | See Output Schema section |

### 2. Create the Agent File

Create `agents/<slug>.py` following this template:

```python
"""<AgentName> Agent
====================
<One-line purpose>
"""

from agno.agent import Agent
from app.settings import default_model
from db import get_surrealdb

# Import tools, knowledge, context providers as needed

INSTRUCTIONS = """\
<Clear, specific instructions for the agent>
"""

my_agent = Agent(
    id="my-agent",                    # kebab-case, used as API endpoint path
    name="My Agent",                   # Human-readable display name
    model=default_model(),             # Fresh model instance per agent
    db=get_surrealdb(),                # SurrealDB for sessions/memory
    tools=[...],                       # See Tools section
    instructions=INSTRUCTIONS,
    # --- Recommended defaults ---
    enable_agentic_memory=True,        # Agent manages user memories
    add_datetime_to_context=True,      # Time awareness
    add_history_to_context=True,       # Conversation continuity
    num_history_runs=5,                # Last 5 runs in context
    markdown=True,                     # Format output as markdown
)
```

### 3. Add Tools

**Python functions** (first-class citizens — no wrapper needed):

```python
from agno.tools import tool  # Not required; plain functions work

def lookup_user(user_id: str) -> str:
    """Look up a user by ID."""
    return f"User {user_id}: Alice"

agent = Agent(tools=[lookup_user], ...)
```

**Pre-built toolkits** (100+ available):

```python
from agno.tools.hackernews import HackerNewsTools
from agno.tools.duckduckgo import DuckDuckGoTools
from agno.tools.website import WebsiteTools

agent = Agent(tools=[HackerNewsTools(), DuckDuckGoTools()], ...)
```

**Custom Toolkit** (grouped functions with shared state):

```python
from agno.tools import Toolkit

class MyTools(Toolkit):
    def __init__(self):
        super().__init__(name="my_tools")
        self.register(self.lookup_user)
        self.register(self.update_user)

    def lookup_user(self, user_id: str) -> str:
        """Look up a user by ID."""
        ...

    def update_user(self, user_id: str, data: str) -> str:
        """Update user data."""
        ...
```

**MCP tools** (external tool servers):

```python
from agno.tools.mcp import MCPTools

# Streamable HTTP (recommended)
mcp = MCPTools(url="https://example.com/mcp", transport="streamable-http")

# Or stdio
mcp = MCPTools(command="npx", args=["-y", "@modelcontextprotocol/server-filesystem", "/tmp"])
```

> ⚠️ In AgentOS, MCP lifecycle is handled automatically. Do **not** use `reload=True` with MCPTools.

**Context providers** (reduce tool surface):

```python
from agno.context.workspace import WorkspaceContextProvider

ctx = WorkspaceContextProvider(
    id="my-codebase",
    name="My Codebase",
    root=Path(__file__).resolve().parents[1],
    model=default_model(),
)

agent = Agent(
    tools=ctx.get_tools(),
    instructions=MY_INSTRUCTIONS + "\n\n" + ctx.instructions(),
    ...
)
```

### 4. Add Memory

```python
# Agentic memory — agent creates/updates/deletes memories per run
agent = Agent(enable_agentic_memory=True, ...)

# Update memories at end of each run (lighter weight alternative)
agent = Agent(update_memory_on_run=True, ...)

# Add memories to context so agent references them
agent = Agent(add_memories_to_context=True, ...)

# Session summaries — auto-summarize conversations
agent = Agent(
    enable_session_summaries=True,
    add_session_summary_to_context=True,
    ...
)
```

### 5. Add Knowledge (RAG)

```python
from db import create_surrealdb_knowledge

my_kb = create_surrealdb_knowledge("My Knowledge", "my_vectors")

agent = Agent(
    knowledge=my_kb,
    add_knowledge_to_context=True,   # Enable RAG
    search_knowledge=True,            # Agent can search (default True)
    update_knowledge=False,           # Agent can add docs (default False)
    ...
)
```

For standalone knowledge (not per-agent):

```python
from agno.knowledge import Knowledge
from agno.knowledge.embedder.openai import OpenAIEmbedder
from agno.vectordb.surrealdb import SurrealDb as SurrealVectorDb

knowledge = Knowledge(
    name="My Knowledge",
    vector_db=SurrealVectorDb(
        client=surreal_client,
        collection="my_vectors",
        embedder=OpenAIEmbedder(id="text-embedding-3-small"),
    ),
)
```

### 6. Configure Structured Output

```python
from pydantic import BaseModel

class MyOutput(BaseModel):
    title: str
    summary: str
    tags: list[str]

agent = Agent(
    output_schema=MyOutput,           # Response parsed into Pydantic model
    ...
)
```

**Advanced output options:**

```python
agent = Agent(
    output_schema=MyOutput,
    output_model="openai:gpt-4o",    # Separate model for final formatting
    output_model_prompt="Format as MyOutput",
    parser_model="openai:gpt-4o-mini", # Cheaper model to parse response
    ...
)
```

> ⚠️ When `output_schema` is set, `agent.run().content` returns a **Pydantic model instance**, not a string. Handle accordingly in downstream code.

### 7. Add Session State

```python
# Static initial state
agent = Agent(
    session_state={"shopping_list": [], "budget": 100},
    add_session_state_to_context=True,
    ...
)

# Agentic state — agent can modify state via tools
agent = Agent(
    session_state={"shopping_list": [], "budget": 100},
    enable_agentic_state=True,
    add_session_state_to_context=True,
    ...
)
```

### 8. Add Guardrails

```python
from agno.guardrails import InputGuardrail, OutputGuardrail

# Built-in guardrails
from agno.guardrails.predefined import (
    PIIGuardrail,
    PromptInjectionGuardrail,
    OpenAIModerationGuardrail,
)

agent = Agent(
    pre_hooks=[
        PIIGuardrail(),                    # Block PII in input
        PromptInjectionGuardrail(),         # Block prompt injection
    ],
    post_hooks=[
        OpenAIModerationGuardrail(),       # Check output safety
    ],
    ...
)

# Custom guardrail
from agno.guardrails import BaseGuardrail

class MyGuardrail(BaseGuardrail):
    def check(self, run_input):
        # Return None to pass, or raise to block
        ...

agent = Agent(pre_hooks=[MyGuardrail()], ...)
```

### 9. Configure Compression

```python
# Auto-compress tool results when context gets large
agent = Agent(
    compress_tool_results=True,           # Enable compression
    ...
)

# Custom compression manager
from agno.compression import CompressionManager

agent = Agent(
    compress_tool_results=True,
    compression_manager=CompressionManager(...),
    ...
)

# Token-based compression limit
agent = Agent(
    compress_tool_results=True,
    compress_token_limit=8000,            # Compress when estimated tokens exceed this
    ...
)
```

### 10. Add Reasoning

```python
# Enable step-by-step reasoning
agent = Agent(
    reasoning=True,                       # Enable reasoning mode
    reasoning_model="openai:o3-mini",     # Optional: separate reasoning model
    reasoning_min_steps=1,
    reasoning_max_steps=10,
    ...
)
```

### 11. Register in AgentOS

Add to `app/main.py`:

```python
from agents.my_agent import my_agent

agent_os = AgentOS(
    ...
    agents=[..., my_agent],
    ...
)
```

Add quick prompts to `app/config.yaml`:

```yaml
my-agent:
  - "What can you help me with?"
  - "Tell me about..."
```

Restart: `docker compose restart agentos-api`

### 12. Test Locally

```bash
# Ensure Docker is running
docker compose up -d --build

# Test via API
curl -X POST http://localhost:8006/v1/runs \
  -H "Content-Type: application/json" \
  -d '{"agent_id": "my-agent", "message": "Hello!"}'
```

## Agent Constructor Quick Reference

| Parameter | Type | Default | Purpose |
|-----------|------|---------|---------|
| `id` | `str` | auto UUID | API endpoint path (kebab-case) |
| `name` | `str` | None | Display name |
| `model` | `Model \| str` | None | LLM model instance or `"provider:id"` string |
| `instructions` | `str \| list \| Callable` | None | System instructions |
| `tools` | `list` | None | Tool functions, Toolkits, MCPTools |
| `db` | `BaseDb` | None | Session/memory persistence |
| `knowledge` | `Knowledge` | None | RAG knowledge base |
| `enable_agentic_memory` | `bool` | False | Agent manages user memories |
| `update_memory_on_run` | `bool` | False | Auto-update memories at run end |
| `add_memories_to_context` | `bool` | None | Include memories in context |
| `enable_session_summaries` | `bool` | False | Auto-summarize sessions |
| `add_session_summary_to_context` | `bool` | None | Include summaries in context |
| `session_state` | `dict` | None | Initial session state |
| `add_session_state_to_context` | `bool` | False | Include state in context |
| `enable_agentic_state` | `bool` | False | Agent can modify session state |
| `add_history_to_context` | `bool` | False | Include chat history |
| `num_history_runs` | `int` | None | How many past runs to include |
| `add_datetime_to_context` | `bool` | False | Include current datetime |
| `add_location_to_context` | `bool` | False | Include current location |
| `output_schema` | `BaseModel \| dict` | None | Structured output (Pydantic or JSON Schema) |
| `input_schema` | `BaseModel` | None | Validate input against schema |
| `output_model` | `Model \| str` | None | Separate model for final response |
| `parser_model` | `Model \| str` | None | Model to parse response into schema |
| `markdown` | `bool` | False | Format output as markdown |
| `reasoning` | `bool` | False | Enable step-by-step reasoning |
| `reasoning_model` | `Model \| str` | None | Separate model for reasoning |
| `compress_tool_results` | `bool` | False | Compress tool call history |
| `compression_manager` | `CompressionManager` | None | Custom compression logic |
| `pre_hooks` | `list` | None | Guardrails/evals before processing |
| `post_hooks` | `list` | None | Guardrails/evals after output |
| `tool_call_limit` | `int` | None | Max tool calls per run |
| `dependencies` | `dict` | None | Injected into tools and prompt functions |
| `add_dependencies_to_context` | `bool` | False | Include dependencies in prompt |
| `search_knowledge` | `bool` | True | Agent can search knowledge base |
| `update_knowledge` | `bool` | False | Agent can add to knowledge base |
| `retries` | `int` | 0 | Retry attempts on failure |
| `delay_between_retries` | `int` | 1 | Seconds between retries |
| `exponential_backoff` | `bool` | False | Double delay between retries |

## Key Patterns for This Project

### Model Factory
Always use `default_model()` from `app/settings.py` — never hardcode model IDs in agents.

### Database
Always use `get_surrealdb()` from `db/` — handles connection config from env vars.

### Knowledge
Use `create_surrealdb_knowledge(name, collection)` from `db/` for RAG — sets up SurrealDB vector store with OpenAI embeddings.

### MCP in AgentOS
AgentOS handles MCP connect/close in its lifespan. Do **not** use `reload=True` with MCPTools.

### Output Schema Gotcha
When `output_schema` is set, `agent.run().content` returns a **Pydantic model instance**, not a string. In workflow executors, check `isinstance(content, MyModel)` before string operations.

## Related Resources

- [Agno docs](https://docs.agno.com) — full framework reference
- [Agno LLM-friendly docs](https://docs.agno.com/llms.txt) — concise overview
- [Agno tools / toolkits](https://docs.agno.com/tools/toolkits) — 100+ integrations
- [Agno model providers](https://docs.agno.com/models) — OpenAI, Anthropic, Google, etc.
- [Agno teams](https://docs.agno.com/teams/overview) — multi-agent routing
- [Agno workflows](https://docs.agno.com/workflows/overview) — deterministic pipelines
- [Agno interfaces](https://docs.agno.com/agent-os/interfaces/overview) — Slack, Discord, Telegram, WhatsApp
- [Agno guardrails](https://docs.agno.com/guardrails/overview) — input/output safety
- [Agno context compression](https://docs.agno.com/compression/overview) — manage context windows
- [Agno HITL](https://docs.agno.com/hitl/overview) — human-in-the-loop
- [Agno context providers](https://docs.agno.com/context-providers/overview) — reduce tool surface