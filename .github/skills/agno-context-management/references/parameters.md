# Context Management Parameters

## System Message Parameters

Full parameter reference for the Agno Agent system message.

| Parameter | Type | Default | Effect |
|-----------|------|---------|--------|
| `description` | `str` | `None` | Added at the start of system message |
| `instructions` | `List[str]` or callable | `None` | Task-specific instructions (static or dynamic) |
| `additional_context` | `str` | `None` | Appended to end of system message |
| `expected_output` | `str` | `None` | Describes desired output format |
| `add_instruction_tags` | `bool` | `True` | Wrap instructions in `<instructions>` tags |
| `system_message` | `str` | `None` | Override the entire system message (ignores all other settings) |
| `build_context` | `bool` | `True` | Disable context building entirely (set `False` + `system_message=None` for no system message) |
| `markdown` | `bool` | `False` | Adds "Use markdown to format your answer" to additional information |
| `add_datetime_to_context` | `bool` | `False` | Adds current datetime to additional information |
| `add_location_to_context` | `bool` | `False` | Adds agent location to additional information |
| `add_name_to_context` | `bool` | `False` | Adds agent name to additional information |
| `add_session_summary_to_context` | `bool` | `False` | Adds conversation summary to context |
| `add_memories_to_context` | `bool` | `False` | Adds user memories to context |
| `add_session_state_to_context` | `bool` | `False` | Adds session state to context |
| `add_knowledge_to_context` | `bool` | `False` | Adds knowledge references to user message |
| `add_dependencies_to_context` | `bool` | `False` | Adds dependencies to user message |
| `add_history_to_context` | `bool` | `False` | Adds chat history to context |
| `num_history_runs` | `int` | `None` | Number of history runs to include (requires `add_history_to_context`) |
| `max_tool_calls_from_history` | `int` | `None` | Max tool calls to keep from history (v2.2.1+) |
| `enable_agentic_memory` | `bool` | `False` | Adds `update_user_memory` tool for agent-managed memories |
| `enable_agentic_state` | `bool` | `False` | Adds `update_session_state` tool for agent-managed state |
| `enable_agentic_knowledge_filters` | `bool` | `False` | Lets agent choose knowledge filters dynamically |

## System Message Construction Order

Static content is placed first for prompt caching:

```
1. Description
2. Role
3. Instructions (in <instructions> tags by default)
4. Additional information (markdown, datetime, location, name)
5. Expected output
6. Additional context
7. Memories from previous interactions
8. Session summary
9. Session state
```

User message additions (separate from system message):

```
- Knowledge references (if add_knowledge_to_context=True)
- Dependencies (if add_dependencies_to_context=True)
- Chat history (if add_history_to_context=True)
- Few-shot examples (additional_input)
```

Toolkit instructions — Toolkits with `instructions` and `add_instructions=True` inject their instructions after `<additional_information>` tags in the system message.

## Context Provider Catalog

| Provider | Import | Read | Write |
|----------|--------|------|-------|
| `FilesystemContextProvider` | `agno.context.fs` | Yes | No |
| `DatabaseContextProvider` | `agno.context.database` | Yes | Yes |
| `WebContextProvider` | `agno.context.web` | Yes | No |
| `SlackContextProvider` | `agno.context.slack` | Yes | Yes |
| `GmailContextProvider` | `agno.context.gmail` | Yes | Yes |
| `GoogleCalendarContextProvider` | `agno.context.calendar` | Yes | Yes |
| `GoogleDriveContextProvider` | `agno.context.gdrive` | Yes | No |
| `MCPContextProvider` | `agno.context.mcp` | Yes | No |
| `WikiContextProvider` | `agno.context.wiki` | Yes | Yes |
| `WorkspaceContextProvider` | `agno.context.workspace` | Yes | No |

## Agentic Features

| Feature | Parameter | Tool Added | Purpose |
|---------|-----------|------------|---------|
| Agentic Memory | `enable_agentic_memory=True` | `update_user_memory` | Agent creates/updates/deletes user memories |
| Agentic State | `enable_agentic_state=True` | `update_session_state` | Agent manages its own session state |
| Agentic Knowledge Filters | `enable_agentic_knowledge_filters=True` | (modifies `search_knowledge_base`) | Agent chooses knowledge filters dynamically |

All three require their corresponding `add_*_to_context=True` flag to inject the data into context.

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| Agent ignores instructions | Too much context, instructions buried in middle | Move critical rules to top, trim prose |
| Agent hallucinates tool names | >20 tools on one agent | Use Context Providers to namespace tools |
| Session state not persisting | Missing `db=` on agent | Add `db=get_surrealdb()` |
| `{key}` not substituted in instructions | Key not in `session_state` or `dependencies` | Add the key to the appropriate dict |
| Context provider sub-agent slow | Using main model for sub-agent | Set `model=` to a cheaper model on the provider |
| `enable_agentic_state` not working | Missing `add_session_state_to_context` | Set both `add_session_state_to_context=True` and `enable_agentic_state=True` |
| `enable_agentic_memory` not working | Missing `add_memories_to_context` | Set both `add_memories_to_context=True` and `enable_agentic_memory=True` |
| `enable_agentic_knowledge_filters` not working | Missing knowledge base | Add `knowledge=` with a knowledge base first |
| Custom provider missing tools | Didn't call `get_tools()` | Use `agent = Agent(tools=provider.get_tools())` |
| MCP provider connection drops | Missing `asetup()`/`aclose()` | Wrap in try/finally with lifecycle calls |
| Prompt cache not warming | Dynamic content at start of system message | Put static content first, dynamic last |
| Dependencies not resolving | Callable returning None | Check callable returns a value |
| Tool calls flooding context | Too many tool results in history | Set `max_tool_calls_from_history=N` |
| No system message at all | `build_context=False` without `system_message` | Set `system_message` or re-enable `build_context` |
| Toolkit instructions not appearing | Missing `add_instructions=True` on Toolkit | Set `add_instructions=True` on the Toolkit constructor |