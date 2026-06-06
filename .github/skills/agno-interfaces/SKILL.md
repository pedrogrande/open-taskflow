---
name: agno-interfaces
description: 'Expose Agno agents, teams, and workflows through chat surfaces and protocols — Slack, Telegram, WhatsApp, Discord, A2A, and AG-UI. Use when adding a messaging interface, configuring webhooks, setting up streaming responses, handling media, testing locally with ngrok, or connecting agents to frontends via AG-UI or other agents via A2A.'
argument-hint: 'Interface type and target, e.g. "Slack — expose code-search agent with streaming"'
user-invocable: true
---

# Agno Interfaces

Expose agents, teams, and workflows through chat surfaces and inter-agent protocols. Each interface is a FastAPI router that mounts protocol-specific endpoints on an AgentOS instance.

## When to Use

- Exposing an agent on Slack, Telegram, WhatsApp, or Discord
- Connecting a custom frontend to an agent via AG-UI
- Enabling agent-to-agent communication via A2A protocol
- Adding streaming responses to a chat surface
- Handling media (images, audio, video, documents) in chat
- Testing an interface locally with ngrok

## Available Interfaces

| Interface | Use Case | Setup Complexity |
|-----------|----------|-----------------|
| **Slack** | Team chat, DMs, channel mentions, thread sessions | Medium — Slack App + OAuth |
| **Telegram** | Personal assistants, mobile chat, group chat | Low — Bot token from @BotFather |
| **WhatsApp** | Customer support, mobile chat with E2E encryption | Medium — Meta App + Business API |
| **Discord** | Community servers, gaming, custom commands | Low — Bot token from Discord |
| **A2A** | Agent-to-agent communication (Google's protocol) | Low — just set `a2a_interface=True` |
| **AG-UI** | Custom frontends (Dojo, CopilotKit) | Low — install `ag-ui-protocol` |

## Procedure

### 1. Choose the Interface

```
Where are your users?
├── Internal team → Slack
├── Mobile / personal → Telegram or WhatsApp
├── Community / gaming → Discord
├── Another AI agent → A2A
├── Custom web frontend → AG-UI
└── Multiple surfaces → Add multiple interfaces to one AgentOS
```

Each interface wraps an agent, team, or workflow. Multiple interfaces can share the same AgentOS instance.

### 2. Add an Interface to AgentOS

Interfaces are added to the `interfaces` list in `app/main.py`:

```python
from agno.os import AgentOS
from agno.os.interfaces.slack import Slack

agent_os = AgentOS(
    agents=[my_agent],
    interfaces=[Slack(agent=my_agent)],
)
```

**Each interface takes one of:** `agent=`, `team=`, or `workflow=`.

### 3. Configure Slack

**Prerequisites:**
- Create a Slack App at api.slack.com
- Enable OAuth scopes, event subscriptions, and App Home
- Set webhook URL to `{prefix}/events`
- Install: `uv pip install 'agno[slack]'`

**Environment variables:**

| Variable | Required | Source |
|----------|----------|--------|
| `SLACK_BOT_TOKEN` | Yes | Slack App → OAuth & Permissions |
| `SLACK_SIGNING_SECRET` | Yes | Slack App → Basic Information |

**Agent on Slack:**

```python
from agno.os.interfaces.slack import Slack

interfaces.append(
    Slack(
        agent=code_search,
        streaming=True,              # Stream responses token-by-token
        token=SLACK_BOT_TOKEN,
        signing_secret=SLACK_SIGNING_SECRET,
        resolve_user_identity=True,   # Map Slack user to agent user_id
    )
)
```

**Team on Slack:**

```python
Slack(team=support_team, streaming=True, token=SLACK_BOT_TOKEN, signing_secret=SLACK_SIGNING_SECRET)
```

**Workflow on Slack:**

```python
Slack(workflow=research_workflow, streaming=True, token=SLACK_BOT_TOKEN, signing_secret=SLACK_SIGNING_SECRET)
```

**SlackTools** — let agents search Slack history and send messages:

```python
from agno.tools.slack import SlackTools

agent = Agent(
    tools=[SlackTools(enable_search_messages=True, enable_get_thread=True)],
)
```

### 4. Configure Telegram

**Prerequisites:**
- Create a bot via @BotFather on Telegram
- Get the bot token
- Set webhook URL to `{prefix}/telegram/webhook`

**Environment variables:**

| Variable | Required | Source |
|----------|----------|--------|
| `TELEGRAM_TOKEN` | Yes | @BotFather |
| `TELEGRAM_WEBHOOK_SECRET_TOKEN` | Production only | You choose this string |

**Agent on Telegram:**

```python
from agno.os.interfaces.telegram import Telegram

interfaces.append(
    Telegram(
        agent=my_agent,
        streaming=True,              # Edit messages in real-time
        reply_to_mentions_only=True, # Only respond to @mentions in groups
        reply_to_bot_messages=True,   # Also respond to replies to bot
    )
)
```

**Key parameters:**

| Parameter | Default | Effect |
|-----------|---------|--------|
| `streaming` | `True` | Edit response message in real-time |
| `show_reasoning` | `False` | Show model reasoning as blockquote |
| `reply_to_mentions_only` | `True` | Only respond to @mentions in groups |
| `reply_to_bot_messages` | `True` | Also respond to replies to bot's messages |
| `start_message` | `"Hello!..."` | Response to `/start` command |
| `commands` | `None` | Custom bot commands (auto-registered) |

**Group chat:** By default, bot only responds to @mentions. Set `reply_to_mentions_only=False` to respond to all messages (requires disabling privacy mode via @BotFather).

**Media support:** Inbound (photos, voice, video, documents) and outbound (images, audio, video, files from agent tools).

**TelegramTools** — let agents proactively send messages:

```python
from agno.tools.telegram import TelegramTools

agent = Agent(
    tools=[TelegramTools(chat_id="123456789", all=True)],
)
```

### 5. Configure WhatsApp

**Prerequisites:**
- Create a Meta App at developers.facebook.com
- Configure WhatsApp Business API
- Set webhook URL to `{prefix}/webhook`

**Environment variables:**

| Variable | Required | Source |
|----------|----------|--------|
| `WHATSAPP_ACCESS_TOKEN` | Yes | Meta App Dashboard → WhatsApp → API Setup |
| `WHATSAPP_PHONE_NUMBER_ID` | Yes | WhatsApp → API Setup |
| `WHATSAPP_VERIFY_TOKEN` | Yes | You choose this string for webhook verification |

**Agent on WhatsApp:**

```python
from agno.os.interfaces.whatsapp import Whatsapp

interfaces.append(
    Whatsapp(agent=support_agent)
)
```

**Team on WhatsApp:**

```python
Whatsapp(team=support_team)
```

**Media support:** Text, images, video, audio, documents — both inbound and outbound.

### 6. Configure Discord

**Prerequisites:**
- Create a Discord bot at discord.com/developers
- Get the bot token
- Invite bot to your server

**Environment variables:**

| Variable | Required | Source |
|----------|----------|--------|
| `DISCORD_BOT_TOKEN` | Yes | Discord Developer Portal |

**Agent on Discord:**

```python
from agno.integrations.discord import DiscordClient

discord_agent = DiscordClient(agent=my_agent)
# Discord runs in its own process, not via AgentOS interfaces list
if __name__ == "__main__":
    discord_agent.serve()
```

**Note:** Discord uses `DiscordClient` (not the `interfaces` list). It runs in its own process via `discord.py`.

**Features:**
- Automatic thread creation per conversation
- Media support (images, video, audio, documents)
- Message splitting for responses > 1500 characters
- Reasoning display in italics

### 7. Configure A2A (Agent-to-Agent)

**No prerequisites** — just enable it on AgentOS.

**Simple setup (expose all agents):**

```python
agent_os = AgentOS(
    agents=[my_agent],
    a2a_interface=True,  # Expose all agents/teams/workflows via A2A
)
```

**Selective setup (expose specific agents):**

```python
from agno.os.interfaces.a2a import A2A

a2a = A2A(agents=[my_agent])

agent_os = AgentOS(
    agents=[my_agent],
    interfaces=[a2a],
)
```

**A2A endpoints per agent/team/workflow:**

| Endpoint | Purpose |
|----------|---------|
| `GET /a2a/agents/{id}/.well-known/agent-card.json` | Agent Card (A2A format) |
| `POST /a2a/agents/{id}/v1/message:send` | Run agent (non-streaming) |
| `POST /a2a/agents/{id}/v1/message:stream` | Run agent (streaming) |

**Connect to a remote A2A agent:**

```python
from agno.client.a2a import A2AClient

client = A2AClient("http://localhost:8006/a2a/agents/my-agent")
result = await client.send_message(message="Hello!")
```

**Or use RemoteAgent for a higher-level interface:**

```python
from agno.agent import RemoteAgent

agent = RemoteAgent(base_url="http://localhost:8006", agent_id="my-agent", protocol="a2a")
response = await agent.arun("Hello!")
```

### 8. Configure AG-UI (Custom Frontend)

**Prerequisites:**
- Install: `uv pip install ag-ui-protocol`
- Frontend: Dojo (from ag-ui-protocol repo) or CopilotKit

**Agent via AG-UI:**

```python
from agno.os.interfaces.agui import AGUI

interfaces.append(AGUI(agent=chat_agent))
```

**Team via AG-UI:**

```python
AGUI(team=research_team)
```

**AG-UI endpoints:**

| Endpoint | Purpose |
|----------|---------|
| `POST /agui` | Main entrypoint, accepts `RunAgentInput`, streams AG-UI events |
| `GET /status` | Health/status check |

**Custom events** — stream custom data to the frontend from tools:

```python
from dataclasses import dataclass
from agno.run.agent import CustomEvent

@dataclass
class CustomerProfileEvent(CustomEvent):
    customer_name: str
    customer_email: str

# In a tool:
@tool()
async def get_customer_profile(customer_id: str):
    yield CustomerProfileEvent(customer_name="Alice", customer_email="alice@example.com")
    return "Profile retrieved"
```

### 9. Test Locally with ngrok

For interfaces that use webhooks (Slack, Telegram, WhatsApp), you need a public URL during local development:

```bash
# Install ngrok
brew install ngrok  # or download from ngrok.com

# Start your AgentOS locally
docker compose up -d  # or python -m app.main

# Expose via ngrok
ngrok http 8006
```

Then set the webhook URL to the ngrok URL:
- **Slack**: `{ngrok_url}/events`
- **Telegram**: `{ngrok_url}/telegram/webhook`
- **WhatsApp**: `{ngrok_url}/webhook`

**Register Telegram webhook:**

```bash
curl "https://api.telegram.org/bot${TELEGRAM_TOKEN}/setWebhook?url=${NGROK_URL}/telegram/webhook"
```

### 10. Multiple Interfaces

Add multiple interfaces to a single AgentOS instance:

```python
from agno.os.interfaces.slack import Slack
from agno.os.interfaces.telegram import Telegram
from agno.os.interfaces.a2a import A2A

agent_os = AgentOS(
    agents=[support_agent],
    interfaces=[
        Slack(agent=support_agent, streaming=True, token=SLACK_BOT_TOKEN, signing_secret=SLACK_SIGNING_SECRET),
        Telegram(agent=support_agent, streaming=True),
        A2A(agents=[support_agent]),
    ],
)
```

### 11. Conditional Interface Loading

Load interfaces only when environment variables are set (current project pattern):

```python
# app/main.py
interfaces: list = []

if SLACK_BOT_TOKEN and SLACK_SIGNING_SECRET:
    from agno.os.interfaces.slack import Slack
    interfaces.append(Slack(agent=code_search, streaming=True, token=SLACK_BOT_TOKEN, signing_secret=SLACK_SIGNING_SECRET))

if getenv("TELEGRAM_TOKEN"):
    from agno.os.interfaces.telegram import Telegram
    interfaces.append(Telegram(agent=code_search, streaming=True))

if getenv("WHATSAPP_ACCESS_TOKEN"):
    from agno.os.interfaces.whatsapp import Whatsapp
    interfaces.append(Whatsapp(agent=code_search))

agent_os = AgentOS(
    agents=[code_search],
    interfaces=interfaces,
)
```

## Common Patterns for This Project

### Current Setup
- **Slack** is already wired up in `app/main.py` for `code_search` agent
- Pattern: conditional loading based on env vars (`SLACK_BOT_TOKEN` + `SLACK_SIGNING_SECRET`)

### Adding a New Interface
1. Add env vars to `example.env` and `.env`
2. Add conditional loading in `app/main.py` (follow the Slack pattern)
3. For Railway: add env vars via `scripts/railway/env-sync.sh`
4. Test locally with ngrok before deploying

### Session Persistence
- Interfaces need `db=` on the agent/team for session persistence
- Without a database, sessions reset on server restart
- The `/new` command (Telegram) only works with a database configured

### Container Restart Scope
- Interface changes in `app/main.py` require `docker compose restart agentos-api`
- Agent changes hot-reload, but interface registration does not

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| Slack not responding | Missing env vars or webhook not set | Check `SLACK_BOT_TOKEN` + `SLACK_SIGNING_SECRET` |
| Telegram 403 errors | No webhook secret in production | Set `TELEGRAM_WEBHOOK_SECRET_TOKEN` or use `APP_ENV=development` |
| Telegram bot ignores group messages | Privacy mode enabled (default) | Message @BotFather → `/setprivacy` → Disable |
| WhatsApp webhook verification fails | Wrong `WHATSAPP_VERIFY_TOKEN` | Match the token in Meta App and env var |
| Discord bot not joining server | Wrong permissions or invite URL | Check bot permissions in Developer Portal |
| A2A client can't connect | Wrong base URL | Use `/a2a/agents/{id}/` as base URL |
| AG-UI frontend not connecting | Missing `ag-ui-protocol` package | Run `uv pip install ag-ui-protocol` |
| No session persistence across restarts | Missing `db=` on agent | Add `db=get_surrealdb()` to the agent |
| Streaming not working on Slack | Agents & AI Apps not enabled | Enable in Slack App → App Home settings |
| ngrok URL changes on restart | Free tier generates new URLs | Re-register webhook with new URL |

## Related Resources

- [Agno interfaces overview](https://docs.agno.com/agent-os/interfaces/overview) — all available interfaces
- [Agno Slack interface](https://docs.agno.com/agent-os/interfaces/slack/introduction) — setup, agent/team/workflow
- [Agno Telegram interface](https://docs.agno.com/agent-os/interfaces/telegram/introduction) — webhooks, streaming, groups
- [Agno WhatsApp interface](https://docs.agno.com/agent-os/interfaces/whatsapp/introduction) — Meta App setup, media
- [Agno Discord integration](https://docs.agno.com/integrations/discord/overview) — DiscordClient, threads
- [Agno A2A interface](https://docs.agno.com/agent-os/interfaces/a2a/introduction) — agent-to-agent protocol
- [Agno AG-UI interface](https://docs.agno.com/agent-os/interfaces/ag-ui/introduction) — custom frontends
- [Agno deploy interfaces](https://docs.agno.com/deploy/interfaces) — production deployment guide
- Project: `app/main.py` — current Slack interface setup
- Project: `create-agno-agent` skill — building agents for interfaces
- Project: `create-agno-team` skill — building teams for interfaces