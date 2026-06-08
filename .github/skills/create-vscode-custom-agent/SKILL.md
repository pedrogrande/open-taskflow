---
name: create-vscode-custom-agent
description: 'Create VS Code custom agents (.agent.md files) that define specialized AI personas with scoped tools, model preferences, handoffs, and hooks. Use when creating a new custom agent, configuring tool restrictions for a role, setting up agent handoffs for multi-step workflows, adding agent-scoped hooks, or deciding between agents vs prompt files vs skills.'
argument-hint: 'Agent name and purpose, e.g. "security-reviewer agent" or "plan-then-implement workflow"'
user-invocable: true
---

# Create VS Code Custom Agents

Define specialized AI personas with scoped tools, model preferences, handoffs, and hooks in `.agent.md` files.

## When to Use

- Creating a new custom agent for a specialized role (security reviewer, planner, implementer)
- Restricting which tools an agent can use (read-only, edit-only, web-only)
- Setting up agent handoffs for multi-step workflows (plan → implement → review)
- Adding agent-scoped hooks (auto-format after edits, block dangerous commands)
- Deciding between agents vs prompt files vs skills
- Making an agent available as a subagent only (not in the dropdown)
- Configuring model preferences for specific tasks

## Agents vs Prompt Files vs Skills

| Aspect | Custom Agent | Prompt File | Skill |
|--------|-------------|-------------|-------|
| Persistence | Saved persona, always available | One-off task | Portable capability with scripts |
| Tools | Restricted tool set | Can restrict tools | Full tool access |
| Model | Can specify model preference | Uses current model | Uses current model |
| Handoffs | Can define handoffs to other agents | No handoffs | No handoffs |
| Hooks | Agent-scoped hooks | No hooks | Can have hooks |
| Subagents | Can invoke other agents | No subagents | No subagents |
| Best for | Repeated specialized roles | One-off tasks | Reusable capabilities |

## Procedure

### 1. Choose File Location

| Scope | Location | Available to |
|-------|----------|-------------|
| Workspace | `.github/agents/*.agent.md` | Everyone in the workspace |
| User profile | `~/.copilot/agents/` | You across all workspaces |

VS Code also detects plain `.md` files in `.github/agents/` as custom agents.

> **Tip**: Type `/agents` in chat to quickly open the Agent Customizations editor. Or use **Chat: New Custom Agent** from the Command Palette.

### 2. Write the Frontmatter

The YAML frontmatter configures the agent's identity, tools, and behavior:

```yaml
---
name: Security Reviewer
description: Review code for security vulnerabilities and best practices
argument-hint: 'File path or description of code to review'
tools: ['search/codebase', 'search/usages', 'read/readFile', 'read/problems', 'web/fetch']
user-invocable: true
handoffs:
  - label: Start Implementation
    agent: agent
    prompt: Implement the security fixes outlined above.
    send: false
---
```

**Frontmatter reference:**

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `name` | `str` | Filename | Agent name shown in dropdown |
| `description` | `str` | — | Brief description, shown as placeholder in chat |
| `argument-hint` | `str` | — | Hint text in chat input guiding user interaction |
| `tools` | `list` | All tools | Restricted tool set for this agent |
| `agents` | `list` | All agents | Allowed subagent names. Use `['agent']` to allow the `agent` tool, `[]` to prevent subagents |
| `model` | `str` or `list` | Current model | Model preference. Single string or prioritized list (tries in order) |
| `user-invocable` | `bool` | `true` | Show in agents dropdown. `false` = subagent-only |
| `disable-model-invocation` | `bool` | `false` | Prevent other agents from invoking this as subagent |
| `target` | `str` | `vscode` | Target environment: `vscode` or `github-copilot` |
| `mcp-servers` | `list` | — | MCP server configs for GitHub Copilot target |
| `handoffs` | `list` | — | Suggested next actions after response (see below) |
| `hooks` | `object` | — | Agent-scoped hooks (Preview, requires `chat.useCustomAgentHooks`) |

### 3. Write the Body

The Markdown body is the agent's instructions. It's prepended to every user message when this agent is active.

```markdown
---
name: Planner
description: Generate an implementation plan for new features
tools: ['search/codebase', 'search/usages', 'web/fetch']
---

# Planning Instructions

You are in planning mode. Your task is to generate an implementation plan.

**Rules:**
- Do NOT make any code edits
- Only use read-only tools for research
- Structure your plan with: Overview, Requirements, Steps, Testing
- Reference specific files and line numbers
```

**Body best practices:**

- Start with a clear role definition
- List rules and constraints explicitly
- Reference tools by name using `#tool:<tool-name>` syntax
- Reference other files using Markdown links
- Keep instructions concise — the model is smart

### 4. Configure Tools

Restrict tools to enforce the agent's role. Common patterns:

```yaml
# Read-only research agent
tools: ['search/codebase', 'search/usages', 'read/readFile', 'read/problems', 'web/fetch']

# Code editing agent
tools: ['edit', 'search/codebase', 'read/readFile', 'execute/runInTerminal']

# Web research agent
tools: ['web/fetch', 'search/codebase']

# Coordinator agent (delegates to subagents)
tools: ['agent', 'read/readFile', 'search/codebase']
agents: ['Researcher', 'Implementer', 'Reviewer']
```

**Built-in tool sets and individual tools:**

| Tool Set | Individual Tools |
|----------|-----------------|
| `#agent` | `agent/runSubagent` |
| `#browser` | Browser interaction (experimental) |
| `#edit` | `edit/createDirectory`, `edit/createFile`, `edit/editFiles`, `edit/editNotebook` |
| `#execute` | `execute/createAndRunTask`, `execute/getTerminalOutput`, `execute/runInTerminal`, `execute/runNotebookCell`, `execute/testFailure` |
| `#read` | `read/getNotebookSummary`, `read/problems`, `read/readFile`, `read/readNotebookCellOutput`, `read/terminalLastCommand`, `read/terminalSelection` |
| `#search` | `search/changes`, `search/codebase`, `search/fileSearch`, `search/listDirectory`, `search/textSearch`, `search/usages` |
| `#web` | `web/fetch` |

Additional tools: `#selection`, `#todos`, `#vscode/askQuestions`, `#vscode/extensions`, `#vscode/getProjectSetupInfo`, `#vscode/installExtension`, `#vscode/runCommand`, `#vscode/VSCodeAPI`, `#githubRepo`, `#githubTextSearch`, `#newWorkspace`

MCP tools: Use `<server_name>/*` format to include all tools from an MCP server (e.g., `['mongodb/*']`).

> If a specified tool is not available when the agent runs, it's silently ignored.

### 5. Configure Handoffs

Handoffs create guided workflows between agents. After a response, buttons appear to transition to the next agent:

```yaml
handoffs:
  - label: Start Implementation
    agent: agent
    prompt: Implement the plan outlined above.
    send: false
    model: GPT-5.2 (copilot)
  - label: Review Code
    agent: code-reviewer
    prompt: Review the implementation for quality and security issues.
    send: true
```

| Field | Type | Description |
|-------|------|-------------|
| `label` | `str` | Button text shown to user |
| `agent` | `str` | Target agent identifier |
| `prompt` | `str` | Pre-filled prompt for the next agent |
| `send` | `bool` | Auto-submit the prompt (default: `false`) |
| `model` | `str` | Optional model override for the handoff |

### 6. Configure Subagents

Use the `agents` property to restrict which agents can be invoked as subagents:

```yaml
# Allow specific agents only
agents: ['Researcher', 'Implementer', 'Reviewer']

# Allow all agents (default)
agents: ['*']

# Prevent any subagent use
agents: []
```

**Requirements:**

- Include `'agent'` in `tools` when specifying `agents`
- Self-referential agents (listing themselves) require `chat.subagents.allowInvocationsFromSubagents` enabled
- Nested subagents have a maximum depth of 5

**Visibility control:**

```yaml
# Subagent-only (hidden from dropdown)
user-invocable: false

# Prevent other agents from invoking this
disable-model-invocation: true

# Both: only invokable by explicit user action
user-invocable: true
disable-model-invocation: true
```

### 7. Add Agent-Scoped Hooks (Preview)

Hooks run shell commands at lifecycle points. Agent-scoped hooks only run when this agent is active.

Requires `chat.useCustomAgentHooks` enabled.

```yaml
---
name: Strict Formatter
description: Agent that auto-formats code after every edit
hooks:
  PostToolUse:
    - type: command
      command: "./scripts/format-changed-files.sh"
---
```

**Hook lifecycle events:**

| Event | When | Common Use |
|-------|------|------------|
| `SessionStart` | Session begins | Inject project context |
| `UserPromptSubmit` | User submits prompt | Audit requests |
| `PreToolUse` | Before tool runs | Block dangerous operations, modify input |
| `PostToolUse` | After tool completes | Run formatters, log results |
| `PreCompact` | Before context compaction | Save important context |
| `SubagentStart` | Subagent spawned | Track nested usage |
| `SubagentStop` | Subagent completes | Aggregate results |
| `Stop` | Session ends | Generate reports, cleanup |

**Advanced**: See [references/hooks.md](references/hooks.md) for hook input/output format, exit codes, and usage scenarios.

### 8. Generate with AI

Type `/create-agent` in Agent mode chat and describe the persona. The agent asks clarifying questions and generates the `.agent.md` file.

You can also extract an agent from an ongoing conversation: after a productive multi-turn session, ask "make an agent for this kind of task."

## Common Patterns

### Read-Only Research Agent

```markdown
---
name: Researcher
description: Research codebase patterns and gather context
tools: ['search/codebase', 'search/usages', 'read/readFile', 'web/fetch']
---
Research thoroughly using read-only tools. Return a structured summary of findings with file paths and line numbers.
```

### Coordinator with Specialized Workers

```markdown
---
name: Feature Builder
description: Build features by researching first, then implementing
tools: ['agent', 'edit', 'search/codebase', 'read/readFile']
agents: ['Researcher', 'Implementer', 'Reviewer']
---
You are a feature builder. For each task:
1. Use the Researcher agent to gather context
2. Use the Implementer agent to make code changes
3. Use the Reviewer agent to check quality
```

### Plan-Then-Implement Workflow

```markdown
---
name: Planner
description: Generate an implementation plan for new features
tools: ['search/codebase', 'search/usages', 'web/fetch']
model: ['Claude Opus 4.5', 'GPT-5.2']
handoffs:
  - label: Implement Plan
    agent: agent
    prompt: Implement the plan outlined above.
    send: false
---
You are in planning mode. Generate a structured plan. Do NOT make code edits.
```

### Subagent-Only Helper

```markdown
---
name: internal-helper
description: Internal helper for specialized tasks
user-invocable: false
tools: ['search/codebase', 'read/readFile']
---
This agent can only be invoked as a subagent by other agents.
```

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| Agent not in dropdown | `user-invocable: false` or wrong file location | Set `user-invocable: true` and check `.github/agents/` |
| Agent can't use tools | Tool names incorrect | Use exact tool names from `#` picker in chat |
| Handoff button not appearing | Wrong `agent` identifier | Use the exact agent name or `agent` for default |
| Hooks not running | `chat.useCustomAgentHooks` not enabled | Enable the setting in VS Code |
| Subagent can't invoke others | Nested subagents disabled | Enable `chat.subagents.allowInvocationsFromSubagents` |
| Model not found | Model name format wrong | Use format like `GPT-5.2 (copilot)` or `Claude Sonnet 4.5 (copilot)` |
| 128 tools limit error | Too many MCP tools enabled | Deselect tools or entire MCP servers in tools picker |

## Related Resources

- [VS Code custom agents docs](https://code.visualstudio.com/docs/copilot/customization/custom-agents) — full reference
- [VS Code subagents docs](https://code.visualstudio.com/docs/copilot/agents/subagents) — orchestration patterns
- [VS Code agent tools docs](https://code.visualstudio.com/docs/copilot/agents/agent-tools) — tool reference
- [VS Code hooks docs](https://code.visualstudio.com/docs/copilot/customization/hooks) — hook lifecycle and configuration
- [Awesome Copilot agents](https://github.com/github/awesome-copilot/tree/main) — community examples
