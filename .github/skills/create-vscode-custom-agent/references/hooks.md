# Agent Hooks Reference

Detailed reference for VS Code agent hooks — input/output format, exit codes, and usage scenarios.

## Hook Configuration Format

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "type": "command",
        "command": "./scripts/validate-tool.sh",
        "timeout": 15
      }
    ],
    "PostToolUse": [
      {
        "type": "command",
        "command": "npx prettier --write \"$TOOL_INPUT_FILE_PATH\""
      }
    ]
  }
}
```

### Hook Command Properties

| Property | Type | Description |
|----------|------|-------------|
| `type` | string | Must be `"command"` |
| `command` | string | Default command to run (cross-platform) |
| `windows` | string | Windows-specific command override |
| `linux` | string | Linux-specific command override |
| `osx` | string | macOS-specific command override |
| `cwd` | string | Working directory (relative to repo root) |
| `env` | object | Additional environment variables |
| `timeout` | number | Timeout in seconds (default: 30) |

## Hook Input Format

Every hook receives JSON via stdin with common fields:

```json
{
  "timestamp": "2026-02-09T10:30:00.000Z",
  "cwd": "/path/to/workspace",
  "sessionId": "session-identifier",
  "hookEventName": "PreToolUse",
  "transcript_path": "/path/to/transcript.json"
}
```

### PreToolUse additional fields

```json
{
  "tool_name": "editFiles",
  "tool_input": { "files": ["src/main.ts"] },
  "tool_use_id": "tool-123"
}
```

### PostToolUse additional fields

```json
{
  "tool_name": "editFiles",
  "tool_input": { "files": ["src/main.ts"] },
  "tool_use_id": "tool-123",
  "tool_response": "File edited successfully"
}
```

### SessionStart additional fields

```json
{
  "source": "new"
}
```

### SubagentStart additional fields

```json
{
  "agent_id": "subagent-456",
  "agent_type": "Plan"
}
```

### Stop additional fields

```json
{
  "stop_hook_active": false
}
```

## Hook Output Format

### Common output fields

```json
{
  "continue": true,
  "stopReason": "Security policy violation",
  "systemMessage": "Unit tests failed"
}
```

| Field | Type | Description |
|-------|------|-------------|
| `continue` | bool | Set `false` to stop processing (default: `true`) |
| `stopReason` | string | Reason for stopping, shown to user |
| `systemMessage` | string | Warning message displayed to user |

### Exit Codes

| Code | Behavior |
|------|----------|
| `0` | Success: parse stdout as JSON |
| `2` | Blocking error: stop processing, show error to model |
| Other | Non-blocking warning: show warning, continue |

### PreToolUse output

```json
{
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "permissionDecision": "deny",
    "permissionDecisionReason": "Destructive command blocked by policy",
    "updatedInput": { "files": ["src/safe.ts"] },
    "additionalContext": "User has read-only access"
  }
}
```

| Field | Values | Description |
|-------|--------|-------------|
| `permissionDecision` | `"allow"`, `"deny"`, `"ask"` | Controls tool approval |
| `permissionDecisionReason` | string | Reason shown to user |
| `updatedInput` | object | Modified tool input (optional) |
| `additionalContext` | string | Extra context for the model |

**Priority**: When multiple hooks run, most restrictive wins: `deny` > `ask` > `allow`.

### PostToolUse output

```json
{
  "decision": "block",
  "reason": "Post-processing validation failed",
  "hookSpecificOutput": {
    "hookEventName": "PostToolUse",
    "additionalContext": "The edited file has lint errors"
  }
}
```

### Stop output

```json
{
  "hookSpecificOutput": {
    "hookEventName": "Stop",
    "decision": "block",
    "reason": "Run the test suite before finishing"
  }
}
```

> **Important**: When a `Stop` hook blocks, the agent continues running and consumes premium requests. Always check `stop_hook_active` to prevent infinite loops.

## Hook File Locations

| Scope | Location |
|-------|----------|
| Workspace | `.github/hooks/*.json` |
| User | `~/.copilot/hooks` |
| Agent-scoped | `hooks` field in `.agent.md` frontmatter |

Custom locations via `chat.hookFilesLocations` setting:

```json
"chat.hookFilesLocations": {
  ".github/hooks": true,
  "custom/hooks": true,
  "~/my-hooks/security.json": true
}
```

## Usage Scenarios

### Block dangerous commands

```bash
#!/bin/bash
INPUT=$(cat)
TOOL_NAME=$(echo "$INPUT" | jq -r '.tool_name')
TOOL_INPUT=$(echo "$INPUT" | jq -r '.tool_input')

if [ "$TOOL_NAME" = "runTerminalCommand" ]; then
  COMMAND=$(echo "$TOOL_INPUT" | jq -r '.command // empty')
  if echo "$COMMAND" | grep -qE '(rm\s+-rf|DROP\s+TABLE|DELETE\s+FROM)'; then
    echo '{"hookSpecificOutput":{"permissionDecision":"deny","permissionDecisionReason":"Destructive command blocked"}}'
    exit 0
  fi
fi
echo '{"continue":true}'
```

### Auto-format after edits

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "type": "command",
        "command": "./scripts/format-changed-files.sh",
        "timeout": 30
      }
    ]
  }
}
```

### Inject project context at session start

```bash
#!/bin/bash
PROJECT_INFO=$(cat package.json 2>/dev/null | jq -r '.name + " v" + .version' || echo "Unknown")
BRANCH=$(git branch --show-current 2>/dev/null || echo "unknown")

cat <<EOF
{
  "hookSpecificOutput": {
    "hookEventName": "SessionStart",
    "additionalContext": "Project: $PROJECT_INFO | Branch: $BRANCH"
  }
}
EOF
```

---
