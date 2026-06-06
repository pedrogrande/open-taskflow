---
name: create-agno-team
description: 'Build Agno teams — multi-agent groups that collaborate through coordinate, route, broadcast, or tasks modes. Use when creating teams, adding member agents, configuring delegation, sharing session state, adding knowledge/guardrails/skills to team leaders, or registering teams in AgentOS. Covers TeamMode, nested teams, callable factories, TeamFactory, and best practices for the agno-surrealdb-railway stack.'
argument-hint: 'Team purpose and member roles, e.g. "research team — news + finance + writer agents"'
user-invocable: true
---

# Create Agno Teams

Build multi-agent teams where a leader coordinates specialized member agents. Covers the four team modes, member design, session state, knowledge, guardrails, structured output, and registration in AgentOS.

## When to Use

- Multiple specialized agents need to collaborate on a task
- A single agent's context window gets exceeded
- You want automatic routing to the right specialist
- You need multiple perspectives on the same topic (broadcast)
- You want an autonomous task loop that decomposes goals
- You need per-tenant or per-user team composition (TeamFactory)

## Team vs Agent vs Workflow

| Primitive | When | Determinism | Cost |
|-----------|------|-------------|------|
| **Agent** | Single domain, one model | Low — model decides | Low |
| **Team** | Multiple specialists, leader decides who | Medium — leader routes | Medium |
| **Workflow** | Fixed steps, known order | High — you define the flow | High (but predictable) |

> **Rule of thumb:** Start with an agent. Add a team when routing/delegation matters. Use a workflow when the process must run the same way every time.

## Procedure

### 1. Choose the Team Mode

```python
from agno.team.mode import TeamMode
```

| Mode | Behavior | Token Cost | When to Use |
|------|----------|-----------|-------------|
| `coordinate` (default) | Leader selects members, formulates tasks, synthesizes results | High | Quality matters, leader adds reasoning |
| `route` | Leader picks one member, returns their response directly | Low | Simple routing, cost-sensitive |
| `broadcast` | Leader delegates same task to all members simultaneously | Medium | Multiple perspectives, parallel research |
| `tasks` | Leader decomposes goal into tasks, executes iteratively | High | Multi-step goals with dependencies |

**Decision flow:**

```
Need a team?
├── Know which member should handle each request?
│   └── Yes → mode="route" (fast, cheap)
├── Need multiple perspectives on the same topic?
│   └── Yes → mode="broadcast" (parallel research)
├── Need the leader to decompose a complex goal?
│   └── Yes → mode="tasks" (autonomous loop)
└── Otherwise → mode="coordinate" (default, leader decides)
```

### 2. Define Member Agents

Each member needs a `name`, `role`, and (optionally) an `id`. The leader uses `role` to decide who handles what.

```python
from agno.agent import Agent
from app.settings import default_model

news_agent = Agent(
    id="news-agent",                              # Stable ID for tracing
    name="News Agent",                            # Human-readable
    role="Get trending tech news from HackerNews", # Leader reads this
    model=default_model(),
    tools=[HackerNewsTools()],
)

finance_agent = Agent(
    id="finance-agent",
    name="Finance Agent",
    role="Get stock prices and financial data",
    model=default_model(),
    tools=[YFinanceTools()],
)
```

**Member design rules:**
- `role` must be specific enough for the leader to route correctly
- Set `id` for stable delegation identity (otherwise Agno uses `name`)
- Members inherit the team's model if not explicitly set
- Each member can have its own tools, knowledge, and instructions
- Members can be Agents or other Teams (nested teams)

### 3. Create the Team

```python
from agno.team import Team
from agno.team.mode import TeamMode
from db import get_surrealdb

research_team = Team(
    id="research-team",
    name="Research Team",
    mode=TeamMode.coordinate,
    model=default_model(),
    members=[news_agent, finance_agent],
    instructions=[
        "Delegate to the appropriate agent based on the request.",
        "Synthesize findings into a clear, structured report.",
    ],
    db=get_surrealdb(),
    markdown=True,
    add_datetime_to_context=True,
)
```

**Key constructor parameters:**

| Parameter | Type | Default | Purpose |
|-----------|------|---------|---------|
| `members` | `list[Agent \| Team]` | required | Agents or sub-teams |
| `mode` | `TeamMode` | `coordinate` | Delegation strategy |
| `model` | `Model \| str` | None | Leader model (members inherit if not set) |
| `instructions` | `str \| list[str]` | None | Guide the leader's coordination |
| `db` | `BaseDb` | None | Persist sessions, state, memory |
| `session_state` | `dict` | None | Shared state across members |
| `output_schema` | `BaseModel` | None | Constrain final response to Pydantic model |
| `knowledge` | `Knowledge` | None | Knowledge base for the leader |
| `tools` | `list` | None | Tools for the leader (not members) |
| `pre_hooks` | `list` | None | Guardrails / validation before processing |
| `post_hooks` | `list` | None | Processing after output |
| `add_history_to_context` | `bool` | False | Add conversation history to leader context |
| `num_history_runs` | `int` | None | How many past runs to include |
| `share_member_interactions` | `bool` | False | Members see each other's responses |
| `determine_input_for_members` | `bool` | True | Leader crafts task for members (False = passthrough) |
| `max_iterations` | `int` | 10 | Cap for tasks mode loop |
| `enable_agentic_memory` | `bool` | False | Team can manage user memories |
| `reasoning` | `bool` | False | Leader plans before delegating |

### 4. Configure Delegation

**Coordinate mode** — leader selects, tasks, synthesizes:

```python
team = Team(
    name="Research Team",
    mode=TeamMode.coordinate,
    members=[news_agent, finance_agent],
    instructions="Research the topic thoroughly, then synthesize findings.",
)
```

**Route mode** — leader picks one member, returns directly:

```python
team = Team(
    name="Language Router",
    mode=TeamMode.route,
    members=[english_agent, japanese_agent, german_agent],
    determine_input_for_members=False,  # Pass user input unchanged
)
```

**Broadcast mode** — all members work on the same task:

```python
team = Team(
    name="Research Team",
    mode=TeamMode.broadcast,
    members=[hn_researcher, arxiv_researcher, web_researcher],
    instructions="Synthesize findings from all researchers into a comprehensive report.",
)
# Use async for concurrent execution
response = await team.arun("Research the current state of AI agents")
```

**Tasks mode** — autonomous task loop:

```python
team = Team(
    name="Ops Team",
    mode=TeamMode.tasks,
    members=[research_agent, writer_agent],
    max_iterations=6,  # Safety cap
)
```

### 5. Add Session State

Session state is shared between the leader and all members. Updates are automatically persisted to the database.

```python
team = Team(
    name="Shopping Team",
    members=[shopping_agent, budget_agent],
    session_state={"shopping_list": [], "budget": 100},
    db=get_surrealdb(),
)
```

Members access state via `run_context` in tools:

```python
from agno.run import RunContext

def add_item(run_context: RunContext, item: str) -> str:
    """Add an item to the shopping list."""
    run_context.session_state["shopping_list"].append(item)
    return f"Added '{item}'"
```

**State options:**

| Parameter | Effect |
|-----------|--------|
| `session_state={}` | Initial shared state |
| `add_session_state_to_context=True` | Leader sees state in context |
| `enable_agentic_state=True` | Team gets tools to update state dynamically |

### 6. Add Knowledge to the Team

The leader can search a knowledge base to inform delegation decisions:

```python
from agno.knowledge.knowledge import Knowledge
from db import create_surrealdb_knowledge

team_knowledge = create_surrealdb_knowledge("Team Knowledge", "team_vectors")

team = Team(
    name="Research Team",
    members=[news_agent, finance_agent],
    knowledge=team_knowledge,
    search_knowledge=True,           # Add search tool to leader
    add_search_knowledge_instructions=True,  # Add search instructions
)
```

**Distributed RAG** — each member has its own knowledge base:

```python
news_knowledge = create_surrealdb_knowledge("News KB", "news_vectors")
finance_knowledge = create_surrealdb_knowledge("Finance KB", "finance_vectors")

news_agent = Agent(name="News Agent", knowledge=news_knowledge, ...)
finance_agent = Agent(name="Finance Agent", knowledge=finance_knowledge, ...)
```

### 7. Add Structured Output

Set `output_schema` on the team to constrain the final synthesized response:

```python
from pydantic import BaseModel, Field

class ResearchReport(BaseModel):
    title: str
    summary: str = Field(description="Executive summary")
    key_insights: list[str]
    recommendation: str

team = Team(
    name="Research Team",
    members=[news_agent, finance_agent],
    output_schema=ResearchReport,
)

response = team.run("Analyze NVDA")
report: ResearchReport = response.content  # Typed Pydantic object
```

**Per-member + per-team schemas:** Members can have their own `output_schema` for consistent intermediate outputs. The team schema controls the final response.

### 8. Add Guardrails

Guardrails run as `pre_hooks` before the team processes input:

```python
from agno.guardrails import PIIGuardrail, PromptInjectionGuardrail

team = Team(
    name="Support Team",
    members=[billing_agent, tech_agent],
    pre_hooks=[PIIGuardrail(), PromptInjectionGuardrail()],
)
```

### 9. Add Chat History

```python
team = Team(
    name="Research Team",
    members=[news_agent, finance_agent],
    db=get_surrealdb(),
    add_history_to_context=True,     # Leader sees conversation history
    num_history_runs=5,              # Last 5 runs
    add_team_history_to_members=True, # Members see team-level history
    num_team_history_runs=3,         # Last 3 team runs sent to members
)
```

**History levels:**
- **Team-level** (`add_history_to_context`): Leader sees past team inputs/outputs
- **Team-to-members** (`add_team_history_to_members`): Members see team-level history
- **Member-level**: Set `add_history_to_context` on individual member agents

### 10. Share Member Interactions

When `share_member_interactions=True`, members can see each other's responses during the current run:

```python
team = Team(
    name="Research Team",
    members=[research_agent, report_agent],
    share_member_interactions=True,  # Report agent sees research results
)
```

### 11. Add Tools to the Leader

The leader can have its own tools (separate from member tools):

```python
from agno.tools.reasoning import ReasoningTools
from agno.tools.knowledge import KnowledgeTools

team = Team(
    name="Reasoning Team",
    members=[researcher, analyst],
    tools=[ReasoningTools(add_instructions=True), KnowledgeTools(knowledge=kb)],
)
```

### 12. Nested Teams

Teams can contain other teams. The top-level leader delegates to sub-team leaders:

```python
germanic_team = Team(
    name="Germanic Team",
    role="Handle German and Dutch questions",
    members=[german_agent, dutch_agent],
)

language_team = Team(
    name="Language Team",
    members=[english_agent, chinese_agent, germanic_team],
)
```

### 13. Callable Factories (Dynamic Members)

Pass a function instead of a static list. Called at the start of each run:

```python
def pick_members(session_state: dict):
    if session_state.get("needs_research", False):
        return [researcher, writer]
    return [writer]

team = Team(
    name="Content Team",
    members=pick_members,
    cache_callables=False,  # Re-evaluate each run
)
```

Factory parameters are injected by name: `agent`, `team`, `run_context`, `session_state`.

### 14. TeamFactory (Per-Request Teams)

For multi-tenant or per-user teams, use `TeamFactory` and register in AgentOS:

```python
from agno.factory import TeamFactory, RequestContext

def build_support_team(ctx: RequestContext) -> Team:
    user_id = ctx.user_id or "anonymous"
    return Team(
        name=f"Support Team for {user_id}",
        members=[billing_agent, tech_agent],
        db=get_surrealdb(),
    )

support_factory = TeamFactory(
    id="support-team",
    db=get_surrealdb(),
    factory=build_support_team,
    name="Per-tenant Support Team",
)
```

### 15. Register in AgentOS

**Static team** — add to the `teams` list:

```python
# app/main.py
from agno.os import AgentOS

agent_os = AgentOS(
    name="AgentOS",
    agents=[web_search, code_search],
    workflows=[design_spec_workflow],
    teams=[research_team],  # Add here
    # ... rest of config
)
```

**Dynamic team** — register the factory:

```python
agent_os = AgentOS(
    teams=[support_factory],  # TeamFactory instead of Team
)
```

**Add prompts to config.yaml:**

```yaml
teams:
  research-team:
    suggestions:
      - "What are the trending AI stories?"
      - "Analyze NVDA stock performance and recent news"
```

### 16. Run the Team

```python
# Sync
response = research_team.run("What's happening with AI stocks?")
print(response.content)

# Streaming
for chunk in research_team.run("Analyze AI trends", stream=True):
    print(chunk.content, end="", flush=True)

# Async (members run concurrently)
response = await research_team.arun("Research AI frameworks")

# With user/session tracking
response = research_team.run(
    "Get my report",
    user_id="user@example.com",
    session_id="session_123",
)

# Per-run output_schema override
response = research_team.run("Analyze", output_schema=ResearchReport)
```

## Common Patterns for This Project

### Database
- **Team sessions**: `get_surrealdb()` — same as agent sessions
- **Pipeline sessions**: `get_pipeline_db(table_name="team_session")` — SQLite for CAWDP teams

### Model Selection
- **Leader**: `default_model()` (OpenAIResponses for strong coordination)
- **Members**: Inherit from team, or set explicitly (e.g., Ollama for cost savings)
- **Reviewer members**: Use a different model than producer members

### Container Restart Scope
- `agents/<slug>.py` — hot-reloads within ~1s
- Team definitions in separate module — **requires** `docker compose restart agentos-api`
- `app/main.py` — **requires** restart

### Team vs Workflow for CAWDP Pipeline
- **Current**: `design_spec_workflow` uses a Workflow (deterministic write → review loop)
- **When to use a team instead**: If the review process needs flexible routing (e.g., different reviewers for different depth levels), a team would be better

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| Leader responds directly, doesn't delegate | No members, or leader thinks it can answer | Check `members` list, improve `role` descriptions |
| Leader always delegates to same member | Member `role` descriptions too similar | Make roles more specific and distinct |
| Route mode synthesizes instead of returning directly | `respond_directly` not set (legacy) | Use `mode=TeamMode.route` explicitly |
| Broadcast mode runs sequentially | Using `run()` instead of `arun()` | Use `await team.arun()` for concurrent execution |
| Tasks mode loops forever | `max_iterations` too high or goal unclear | Lower `max_iterations`, improve instructions |
| Session state not shared | Missing `db=` on Team | Add `db=get_surrealdb()` |
| Member can't see other members' work | `share_member_interactions` not set | Set `share_member_interactions=True` |
| Structured output is wrong type | Team `output_schema` returns Pydantic model | Handle `isinstance(content, BaseModel)` in consumers |
| TeamFactory builds wrong team | Factory not receiving correct context | Check `RequestContext` fields (`user_id`, `trusted.claims`) |

## Related Resources

- [Agno teams overview](https://docs.agno.com/teams/overview) — what are teams, when to use
- [Agno building teams](https://docs.agno.com/teams/building-teams) — members, modes, features
- [Agno delegation](https://docs.agno.com/teams/delegation) — coordinate, route, broadcast, tasks modes
- [Agno running teams](https://docs.agno.com/teams/running-teams) — run, arun, streaming, events
- [Agno team session state](https://docs.agno.com/state/team/overview) — shared state across members
- [Agno team structured output](https://docs.agno.com/input-output/structured-output/team) — per-member + per-team schemas
- [Agno team knowledge](https://docs.agno.com/knowledge/teams/overview) — knowledge bases for teams
- [Agno team guardrails](https://docs.agno.com/guardrails/overview) — PII, prompt injection, moderation
- [Agno team chat history](https://docs.agno.com/history/team/overview) — history levels, team-to-members
- [Agno TeamFactory](https://docs.agno.com/agent-os/factories/team-factory) — per-request teams
- [Agno workflow vs team FAQ](https://docs.agno.com/faq/When-to-use-a-Workflow-vs-a-Team-in-Agno) — decision guide
- Project: `create-agno-agent` skill — building member agents
- Project: `create-agno-workflow` skill — deterministic pipelines
- Project: `agno-structured-output` skill — output_schema for teams