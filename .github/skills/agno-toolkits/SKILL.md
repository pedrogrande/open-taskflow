---
name: agno-toolkits
description: 'Add, create, and configure Agno tools and toolkits for agents and teams — pre-built toolkits (web search, databases, social, scraping), custom @tool functions, Toolkit classes, MCPTools, tool hooks, caching, filtering, and dynamic tool attachment. Use when an agent needs external capabilities, when building custom tools, when configuring MCP servers, when adding tool hooks for logging or validation, or when filtering which tools an agent can access.'
argument-hint: 'Tool type and purpose, e.g. "custom Toolkit for catalogue search" or "add web search tools to agent"'
user-invocable: true
---

# Agno Tools & Toolkits

Tools are what make agents capable of real-world action. Agno provides 120+ pre-built toolkits and three ways to create custom tools. This skill covers selecting, configuring, and building tools for agents and teams.

## When to Use

- Adding pre-built toolkits (web search, databases, social, scraping) to an agent
- Writing custom `@tool` functions for domain-specific logic
- Building a `Toolkit` class for related tools that share state
- Configuring `MCPTools` for external tool servers
- Adding tool hooks for logging, validation, or state injection
- Filtering which tools from a toolkit an agent can access
- Caching tool results to reduce API calls
- Dynamically adding tools to an agent at runtime

## Three Ways to Create Tools

| Method | When to Use | Example |
|--------|-------------|---------|
| **Python function** | Simple, stateless tool | `def get_weather(city: str) -> str` |
| **`@tool` decorator** | Need hooks, caching, confirmation | `@tool(cache_results=True)` |
| **`Toolkit` class** | Related tools sharing state | `class DecisionToolkit(Toolkit)` |

## Procedure

### 1. Choose: Pre-built or Custom?

```
What does the agent need to do?
├── Search the web → WebSearchTools, DuckDuckGoTools, TavilyTools, etc.
├── Query a database → PostgresTools, DuckDbTools, SQLTools, etc.
├── Interact with SaaS → SlackTools, GitHubTools, JiraTools, etc.
├── Scrape websites → FirecrawlTools, Crawl4AITools, WebsiteTools, etc.
├── Run code → PythonTools, ShellTools, DockerTools
├── Call an MCP server → MCPTools (see §7)
├── Domain-specific logic → Custom @tool or Toolkit (see §2–4)
└── Multiple related tools sharing state → Toolkit class (see §4)
```

### 2. Python Function as Tool

Any Python function can be a tool. Agno auto-generates the JSON schema from type hints and docstrings.

```python
from agno.agent import Agent

def get_top_stories(num_stories: int = 10) -> str:
    """Get top stories from Hacker News.

    Args:
        num_stories: Number of stories to return. Defaults to 10.

    Returns:
        JSON string of top stories.
    """
    # ... implementation ...
    return json.dumps(stories)

agent = Agent(tools=[get_top_stories], markdown=True)
```

**Rules:**

- Always include a descriptive docstring — the LLM reads it to decide when to call the tool
- Include `Args:` section with types — Agno parses these into the JSON schema
- Return a string (JSON string for structured data)
- Type hints are required for parameters

### 3. `@tool` Decorator

Use `@tool` when you need hooks, caching, confirmation, or other control:

```python
from agno.tools import tool

@tool(
    name="fetch_stories",              # Override function name
    description="Get top HN stories",   # Override docstring
    stop_after_tool_call=True,         # Return result immediately, stop agent
    cache_results=True,                # Cache to avoid repeat API calls
    cache_ttl=3600,                    # Cache TTL in seconds
    requires_confirmation=True,         # Pause for user confirmation
    tool_hooks=[logger_hook],          # Pre/post execution hooks
)
def get_top_stories(num_stories: int = 5) -> str:
    """Fetch the top stories from Hacker News."""
    # ... implementation ...
```

**`@tool` parameters:**

| Parameter | Type | Effect |
|-----------|------|--------|
| `name` | `str` | Override function name shown to LLM |
| `description` | `str` | Override docstring shown to LLM |
| `stop_after_tool_call` | `bool` | Stop agent after this tool returns |
| `tool_hooks` | `list[Callable]` | Wrap execution with custom logic |
| `pre_hook` | `Callable` | Run before tool execution |
| `post_hook` | `Callable` | Run after tool execution |
| `requires_confirmation` | `bool` | Pause for user approval before running |
| `requires_user_input` | `bool` | Pause for user input before running |
| `external_execution` | `bool` | Tool runs outside agent loop |
| `show_result` | `bool` | Show tool output in agent response |
| `cache_results` | `bool` | Enable result caching |
| `cache_dir` | `str` | Custom cache directory |
| `cache_ttl` | `int` | Cache time-to-live in seconds (default 3600) |

### 4. Toolkit Class

Use `Toolkit` when tools share state, configuration, or need initialization logic:

```python
from agno.tools.toolkit import Toolkit

class DecisionToolkit(Toolkit):
    def __init__(self, decisions_path: Path | None = None, **kwargs):
        super().__init__(name="decision_tools", **kwargs)
        self.decisions_path = decisions_path or _DEFAULT_PATH
        # Register each method as a tool
        self.register(self.find_decisions_for_output)
        self.register(self.record_decision)
        self.register(self.search_decisions_by_tag)

    def find_decisions_for_output(self, output_id: str) -> str:
        """Find all decisions for a given output ID.

        Args:
            output_id: The catalogue ID (e.g. 'P00-001').

        Returns:
            JSON string of matching decisions.
        """
        # ... uses self.decisions_path ...
```

**Toolkit constructor parameters:**

| Parameter | Type | Effect |
|-----------|------|--------|
| `name` | `str` | Toolkit name (required) |
| `tools` | `List[Callable]` | Sync tool functions |
| `async_tools` | `List[Tuple]` | Async tools as `(method, "tool_name")` pairs |
| `instructions` | `str` | Added to agent context for tool usage guidance |
| `include_tools` | `list[str]` | Only register these tools |
| `exclude_tools` | `list[str]` | Skip these tools |
| `requires_confirmation_tools` | `list[str]` | Tools needing user confirmation |
| `cache_results` | `bool` | Enable in-memory caching |
| `cache_ttl` | `int` | Cache TTL in seconds |
| `auto_register` | `bool` | Auto-register all tools on init |

**Async tools** — provide both sync and async variants:

```python
class APITools(Toolkit):
    def __init__(self, base_url: str, **kwargs):
        tools = [self.fetch_data]
        async_tools = [(self.afetch_data, "fetch_data")]  # Same name, async version
        super().__init__(name="api_tools", tools=tools, async_tools=async_tools, **kwargs)

    def fetch_data(self, endpoint: str) -> dict:
        """Fetch data from API (sync)."""
        ...

    async def afetch_data(self, endpoint: str) -> dict:
        """Fetch data from API (async)."""
        ...
```

Agent uses sync for `agent.run()`, async for `agent.arun()`.

### 4a. Choosing Between `Toolkit` Class and `@tool` Decorator (L-002)

| Signal | Use `Toolkit` class | Use `@tool` decorator |
|--------|--------------------|-----------------------|
| Tools share a DB connection or other resource | ✓ | |
| Tools belong to a logical group (catalogue, decisions) | ✓ | |
| Need to filter tools per agent via `include_tools`/`exclude_tools` | ✓ | |
| Need `instructions=` context about correct tool use | ✓ | |
| Truly standalone, stateless, one-off function | | ✓ |

**DB-backed tools** — always use `Toolkit`:

```python
class CatalogueToolkit(Toolkit):
    def __init__(self, **kwargs):
        self.db = _connect()          # connection opened once at construction
        super().__init__(
            name="catalogue_tools",
            tools=[self.read_catalogue_entry, self.list_catalogue_entries],
            instructions="Use output IDs in format 'P00-001'. Status values: draft | review | approved.",
            **kwargs,
        )

    def read_catalogue_entry(self, output_id: str) -> str:
        """Read a single catalogue entry by output ID."""
        return json.dumps(self.db.select(RecordID("catalogue", output_id)))
```

`self.db` is set once; all methods share it. The `instructions=` string is injected into the agent's system prompt to guide correct use.

### 4b. DB-backed Toolkit Constructor Pattern (L-002)

For toolkits that wrap a SurrealDB connection, always call `_connect()` **before** `super().__init__()`. This warms the connection cache before Agno inspects the method list.

```python
from cawdp_development.db._connection import _connect
from agno.tools.toolkit import Toolkit

class CatalogueToolkit(Toolkit):
    def __init__(self, **kwargs: object) -> None:
        _connect()                         # warm connection FIRST
        super().__init__(
            name="catalogue_tools",
            tools=[self.read_catalogue_entry],
            **kwargs,  # type: ignore[arg-type]  # Toolkit kwargs untyped in Agno
        )
```

The `**kwargs: object` + `# type: ignore[arg-type]` is required because `Toolkit.__init__` has untyped kwargs and mypy strict mode will complain otherwise.

### 4c. Toolkit Name Uniqueness and Cross-Shim Method Prefixing (L-007, L-009)

**Name uniqueness (L-009)**: When a write toolkit and its read shim both appear on the same agent, they must have different `name=` strings. Convention: write toolkit = table name, read shim = table name + `"_read"`.

```python
class DesignSectionToolkit(Toolkit):      # write
    def __init__(self) -> None:
        super().__init__(name="design_section", ...)

class DesignSectionReadToolkit(Toolkit):  # read shim
    def __init__(self) -> None:
        super().__init__(name="design_section_read", ...)
```

**Method name prefixing (L-007)**: When an agent receives two shim toolkits for the same logical operation (e.g. read design sections AND read impl sections), Agno registers tools by method name. A duplicate name silently shadows the first.

```python
# ❌ Collision — second `read_section` registration shadows the first
class DesignSectionReadToolkit(Toolkit):
    def read_section(self, ...) -> str: ...

class ImplSectionReadToolkit(Toolkit):
    def read_section(self, ...) -> str: ...  # shadows DesignSectionReadToolkit.read_section

# ✅ Prefixed — both tools survive on the same agent
class DesignSectionReadToolkit(Toolkit):
    def read_design_section(self, ...) -> str: ...
    def list_design_sections(self, ...) -> str: ...

class ImplSectionReadToolkit(Toolkit):
    def read_impl_section(self, ...) -> str: ...
    def list_impl_sections(self, ...) -> str: ...
```

Rule: any read-only shim toolkit that could coexist with a peer on the same agent MUST prefix its method names with the spec qualifier (`design_`, `impl_`, etc.). Write toolkits are safe because each agent only gets its own write toolkit.

### 4d. List/Dict Parameters Must Accept `str` for JSON String LLM Output (L-022)

Agno validates LLM-generated tool arguments through Pydantic before calling the function body. When a parameter is typed `list[dict[str, str]]`, the LLM often emits a JSON string `'[{"key": "value"}]'` instead of a parsed list. Pydantic raises `Input should be a valid list` and the tool call is aborted — the function body never executes.

```python
# ❌ Strict — LLM passes JSON string; Pydantic rejects it before function body runs
def write_verdict(self, issues: list[dict[str, str]] | None = None) -> str: ...

# ✅ Tolerant — accept string and parse it in the body
def write_verdict(self, issues: list[dict[str, str]] | str | None = None) -> str:
    if isinstance(issues, str):
        try:
            issues = json.loads(issues)
        except json.JSONDecodeError:
            issues = []
    ...
```

The same pattern applies to `dict[...]` parameters — LLMs may also stringify those. Apply this to any `@tool` or Toolkit method that accepts a `list[...]` or `dict[...]` parameter.

### 4e. No `{placeholders}` in Toolkit `_INSTRUCTIONS` or `@tool` Docstrings (L-029)

When an agent has `add_session_state_to_context=True`, Agno interpolates `{key}` placeholders in the **entire assembled context** — not just the agent's `instructions` field. This includes:

- `Toolkit._INSTRUCTIONS` strings
- `@tool` method docstrings (included in LLM function definitions)
- Any other text injected via context providers

```python
# ❌ DANGEROUS — {run_id} will be replaced by session_state["run_id"];
#               {iteration} will be left as a literal if not in session_state,
#               and the LLM will fill it with its own Agno run UUID.
_INSTRUCTIONS = (
    "Use write_verdict with review_run_id format: '{run_id}:{iteration}'."
)

def write_verdict(self, review_run_id: str) -> str:
    """
    Write a verdict. review_run_id must be '{run_id}:{iteration}'.
    """

# ✅ SAFE — plain prose, no {placeholders}
_INSTRUCTIONS = (
    "Use write_verdict with the exact review_run_id from session state. "
    "Do NOT use your Agno run UUID or append any suffix."
)

def write_verdict(self, review_run_id: str) -> str:
    """
    Write a verdict. review_run_id comes from session state — use it exactly as provided.
    """
```

Reinforce the correct value in the agent’s own `instructions` field with an explicit IMPORTANT note so the LLM has an unambiguous source of truth.

### 5. Pre-built Toolkits

Agno ships 120+ toolkits. Install the extras and pass to agent:

```python
from agno.tools.yfinance import YFinanceTools
from agno.tools.hackernews import HackerNewsTools

agent = Agent(
    tools=[
        YFinanceTools(include_tools=["get_stock_price"]),
        HackerNewsTools(cache_results=True),
    ],
)
```

**Categories:**

| Category | Toolkits | Install |
|----------|----------|---------|
| **Search** | WebSearchTools, DuckDuckGoTools, TavilyTools, ExaTools, ArxivTools, WikipediaTools, PerplexityTools | `agno[duckduckgo]`, `agno[tavily]`, etc. |
| **Database** | PostgresTools, DuckDbTools, SQLTools, CSVTools, PandasTools, Neo4jTools | `agno[postgres]`, `agno[duckdb]`, etc. |
| **Social** | SlackTools, DiscordTools, TelegramTools, GmailTools, EmailTools | `agno[slack]`, `agno[discord]`, etc. |
| **Scraping** | FirecrawlTools, Crawl4AITools, WebsiteTools, JinaReaderTools, NewspaperTools | `agno[firecrawl]`, `agno[crawl4ai]`, etc. |
| **Local** | PythonTools, ShellTools, FileTools, DockerTools, CalculatorTools | `agno[python]`, `agno[shell]`, etc. |
| **Media** | DalleTools, ElevenLabsTools, FalTools, ReplicateTools | `agno[dalle]`, `agno[elevenlabs]`, etc. |
| **Productivity** | GitHubTools, JiraTools, LinearTools, NotionTools, GoogleCalendarTools | `agno[github]`, `agno[jira]`, etc. |

Full list: <https://docs.agno.com/tools/toolkits>

### 6. Filtering Tools

Limit which tools from a toolkit an agent can access:

```python
# Include only specific tools
agent = Agent(tools=[GmailTools(include_tools=["get_latest_emails"])])

# Exclude specific tools
agent = Agent(tools=[CalculatorTools(exclude_tools=["exponentiate", "factorial"])])

# On Toolkit class constructor
DecisionToolkit(include_tools=["find_decisions_for_output", "record_decision"])
```

### 7. MCPTools

Connect agents to MCP (Model Context Protocol) servers:

```python
from agno.tools.mcp import MCPTools

# Streamable HTTP transport
mcp_tools = MCPTools(url="https://search.parallel.ai/mcp", transport="streamable-http")

# Stdio transport (local process)
mcp_tools = MCPTools(command="npx", args=["-y", "@modelcontextprotocol/server-filesystem", "/path"])

agent = Agent(tools=[mcp_tools])
```

**Within AgentOS** — lifespan is managed automatically. Do NOT use `reload=True` when serving:

```python
from agno.os import AgentOS

agent_os = AgentOS(agents=[agent_with_mcp])
app = agent_os.get_app()
# Do NOT use reload=True with MCP tools
agent_os.serve(app="main:app")  # NOT reload=True
```

**Refresh connection** if MCP server restarts:

```python
await mcp_tools.refresh_connection()
```

### 8. Tool Hooks

Hooks wrap tool execution for logging, validation, or state injection.

**On agent/team** (applies to ALL tools):

```python
def logger_hook(function_name: str, function_call: Callable, arguments: Dict[str, Any]):
    start = time.time()
    result = function_call(**arguments)
    logger.info(f"{function_name} took {time.time() - start:.2f}s")
    return result

agent = Agent(tools=[...], tool_hooks=[logger_hook])
```

**On specific `@tool`** (only that tool):

```python
@tool(tool_hooks=[logger_hook, validation_hook])
def get_top_stories(num_stories: int) -> str:
    ...
```

**Access RunContext in hooks:**

```python
from agno.run import RunContext

def state_injection_hook(
    run_context: RunContext, function_name: str, function_call: Callable, arguments: Dict[str, Any]
):
    # Read or modify session state before calling the tool
    if run_context.session_state:
        arguments["user_id"] = run_context.session_state.get("user_id")
    return function_call(**arguments)
```

**Available hook parameters** (use exact names):

| Parameter | Type | Available in |
|-----------|------|-------------|
| `function_name` | `str` | All hooks |
| `function_call` | `Callable` | All hooks |
| `arguments` | `Dict[str, Any]` | All hooks |
| `agent` | `Agent` | Agent hooks |
| `team` | `Team` | Team hooks |
| `run_context` | `RunContext` | Both |

**Multiple hooks** execute in order (outer → inner):

```python
agent = Agent(tools=[...], tool_hooks=[logger_hook, confirmation_hook])
# logger_hook wraps confirmation_hook wraps the tool
```

**Pre/post hooks** (alternative to tool_hooks):

```python
@tool(pre_hook=validate_inputs, post_hook=log_result)
def get_stock_price(ticker: str) -> str:
    ...
```

### 8a. Injecting Workflow-Controlled Parameters via Tool Hooks (L-031–L-040)

For pipeline agents, certain parameters (`output_id`, `review_run_id`, `iteration`,
`depth`) are controlled by the workflow — not by the LLM. A tool hook makes wrong
values **impossible**, not just inadvisable.

#### Correct hook signature (L-035)

`function_name: str` is the **second** positional arg. Omitting it causes a TypeError:

```python
# ❌ Wrong — missing function_name
def _inject_hook(run_context, function_call, arguments): ...

# ✅ Correct
def _inject_hook(
    run_context: RunContext,
    function_name: str,
    function_call: Callable,
    arguments: dict[str, Any],
) -> Any:
    ...
```

#### Always inject — don't conditionally override (L-039)

Check `if key in ss` (session_state has it), NOT `if key in arguments and key in ss`
(LLM already provided it). The whole point is to guarantee correctness regardless of
what the LLM does.

```python
ss = run_context.session_state or {}

# ❌ Wrong — only injects if LLM already provided the param (defeats the purpose)
if "review_run_id" in arguments and "run_id" in ss:
    arguments["review_run_id"] = ss["run_id"]

# ✅ Correct — always inject (adds if missing, overrides if wrong)
if "run_id" in ss:
    arguments["review_run_id"] = ss["run_id"]
```

#### Use `inspect.signature` to avoid injecting into tools that don't accept the param (L-040)

Tool hooks fire on **every** tool call for the agent, including read-only tools
(`CatalogueToolkit`, `DecisionToolkit`, etc.) that don't accept `output_id` or
`depth`. Unconditional injection causes `Unexpected keyword argument` Pydantic errors.

```python
import inspect
from typing import Any, Callable

def _fn_accepts(function_call: Callable, param_name: str) -> bool:
    try:
        sig = inspect.signature(function_call)
        if param_name in sig.parameters:
            return True
        return any(
            p.kind == inspect.Parameter.VAR_KEYWORD
            for p in sig.parameters.values()
        )
    except (ValueError, TypeError):
        return False
```

Use it before every injection:

```python
if "output_id" in ss and _fn_accepts(function_call, "output_id"):
    arguments["output_id"] = ss["output_id"]
if "run_id" in ss and _fn_accepts(function_call, "review_run_id"):
    arguments["review_run_id"] = ss["run_id"]
if "iteration" in ss and _fn_accepts(function_call, "iteration"):
    arguments["iteration"] = ss["iteration"]
```

#### Validate constrained values; return error JSON on failure (L-036)

```python
if "verdict" in arguments:
    v = str(arguments["verdict"]).upper().strip()
    if v not in ("PASS", "FAIL"):
        return json.dumps({"error": "Invalid verdict. Only PASS or FAIL accepted."})
    arguments["verdict"] = v
```

The LLM sees the error JSON as the tool result and can self-correct.

#### Keep injected params in Python signatures; remove from docstrings (L-032, L-034)

If you remove injected parameters from the method signature, `function_call(**arguments)`
will fail with unexpected keyword argument errors when the hook tries to inject them.
Instead, keep them in the signature but omit them from the docstring `Args` section:

```python
# ✅ Correct — in signature (required for hook injection), absent from Args
def write_verdict(
    self,
    section_key: str,
    verdict: str,
    findings: str,
    output_id: str = "",       # injected by tool hook — omit from docstring Args
    review_run_id: str = "",   # injected by tool hook — omit from docstring Args
    iteration: int = 0,        # injected by tool hook — omit from docstring Args
) -> str:
    """Write a review verdict for one section.

    Args:
        section_key: Key of the section being reviewed.
        verdict: PASS or FAIL.
        findings: Markdown review findings.

    Note: output_id, review_run_id, and iteration are injected automatically
    from session state by the tool hook — do NOT pass them.
    """
```

Give these defaults (`= ""`, `= 0`) so the LLM's omission doesn't cause a missing
argument error on the rare occasion the hook hasn't fired yet.

### 9. Built-in Parameters in Tools

Agno auto-injects these parameters when present in the function signature:

| Parameter | Type | What it provides |
|-----------|------|-----------------|
| `agent` | `Agent` | The agent instance |
| `team` | `Team` | The team instance |
| `run_context` | `RunContext` | Session state, dependencies, metadata |
| `images` | `list` | Images from the user message |
| `videos` | `list` | Videos from the user message |
| `audio` | `list` | Audio from the user message |
| `files` | `list` | Files from the user message |

```python
def get_agent_model(agent: Agent) -> str:
    """Get the model of the agent."""
    return agent.model.id
```

These are NOT shown to the LLM — Agno injects them automatically.

### 10. Caching

Reduce repeated API calls with result caching:

```python
# On @tool
@tool(cache_results=True, cache_ttl=3600)
def get_stock_price(ticker: str) -> str:
    ...

# On Toolkit
agent = Agent(tools=[HackerNewsTools(cache_results=True)])

# Custom cache directory
@tool(cache_results=True, cache_dir="/tmp/agno_cache")
def expensive_api_call(query: str) -> str:
    ...
```

### 11. Dynamic Tool Attachment

Add or replace tools after agent creation:

```python
# Add a single tool
agent.add_tool(get_weather)

# Replace ALL tools
team.set_tools([get_stock_price, get_stock_availability])
```

`add_tool` extends existing tools. `set_tools` replaces them entirely.

### 12. Tool Call Limit

Limit how many tool calls an agent can make per run:

```python
agent = Agent(tools=[...], tool_call_limit=5)
```

Prevents infinite tool loops. Agent stops after N tool calls even if the model wants more.

## Common Patterns for This Project

### Current Tool Usage

- **`@tool` functions**: `catalogue_tools.py`, `file_tools.py` — simple, stateless tools
- **`Toolkit` class**: `decision_tools.py` — tools sharing `decisions_path` and session state
- **`MCPTools`**: `web_search.py` — Parallel search via MCP endpoint
- **`ParallelTools`**: `web_search.py` — direct SDK when `PARALLEL_API_KEY` is set

### Pattern: @tool for Simple Functions

Use when the tool is stateless and doesn't need initialization:

```python
from agno.tools import tool

@tool
def read_catalogue_entry(output_id: str) -> str:
    """Read a single catalogue entry by output ID."""
    ...
```

### Pattern: Toolkit for Stateful Tools

Use when tools share config, state, or need session_state access:

```python
class DecisionToolkit(Toolkit):
    def __init__(self, decisions_path: Path | None = None, **kwargs):
        super().__init__(name="decision_tools", **kwargs)
        self.decisions_path = decisions_path or _DEFAULT_PATH
        self.register(self.find_decisions_for_output)
        self.register(self.record_decision)
```

### Pattern: Conditional MCPTools

Use when API key availability varies:

```python
if getenv("PARALLEL_API_KEY"):
    web_tools = ParallelTools()
else:
    web_tools = MCPTools(url="https://search.parallel.ai/mcp", transport="streamable-http")
```

### Pattern: Session State in Toolkits

Access `run_context.session_state` for in-workflow state sharing:

```python
def _load_register(self, run_context: RunContext | None = None) -> DecisionRegister:
    if run_context and run_context.session_state:
        cached = run_context.session_state.get("decisions")
        if cached is not None:
            return DecisionRegister(decisions=cached)
    return self._load_from_file()
```

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| LLM never calls the tool | Poor docstring or missing `Args:` | Write descriptive docstring with `Args:` section |
| Tool returns wrong type | Returning non-string | Always return `str`; use `json.dumps()` for structured data |
| `TypeError` on tool call | Missing type hints | Add type hints to all parameters |
| MCP connection drops on reload | `reload=True` with MCPTools | Remove `reload=True` from `agent_os.serve()` |
| Tool not found after `add_tool` | Agent already started | `add_tool` works before or after first run |
| Cache serving stale data | `cache_ttl` too long | Reduce `cache_ttl` or set `cache_results=False` |
| `include_tools` has no effect | Wrong tool names | Use exact method names from the Toolkit class |
| Async tools not used | Missing `async_tools` param | Add `(async_method, "tool_name")` tuples to `async_tools` |
| `RunContext` is `None` in tool | Not in a workflow session | `run_context` only populated during workflow runs |
| `requires_confirmation` hangs | No approval mechanism | Only works with AgentOS approval endpoints or UI |

## Related Resources

- [Agno tools overview](https://docs.agno.com/tools/overview) — how tools work
- [Agno creating tools](https://docs.agno.com/tools/creating-tools/overview) — custom tools guide
- [Agno Python functions as tools](https://docs.agno.com/tools/creating-tools/python-functions) — @tool decorator
- [Agno custom toolkits](https://docs.agno.com/tools/creating-tools/toolkits) — Toolkit class
- [Agno toolkits index](https://docs.agno.com/tools/toolkits/overview) — 120+ pre-built toolkits
- [Agno tool hooks](https://docs.agno.com/tools/hooks) — pre/post hooks
- [Agno tool caching](https://docs.agno.com/tools/caching) — result caching
- [Agno selecting tools](https://docs.agno.com/tools/selecting-tools) — include/exclude
- [Agno MCPTools](https://docs.agno.com/agent-os/mcp/tools) — MCP in AgentOS
- [Agno @tool decorator reference](https://docs.agno.com/reference/tools/decorator) — full parameter list
- [Agno Toolkit reference](https://docs.agno.com/reference/tools/toolkit) — full parameter list
- Project: `cawdp_pipeline/tools/` — existing custom tools
- Project: `agents/web_search.py` — MCPTools pattern
- Project: `create-agno-agent` skill — adding tools to agents
