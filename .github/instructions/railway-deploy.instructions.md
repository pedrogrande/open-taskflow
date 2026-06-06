---
description: "Use when deploying to Railway, provisioning infrastructure, syncing environment variables, or troubleshooting deployment failures. Covers the full deploy lifecycle and common issues."
applyTo: ["scripts/railway/**", "railway.json"]
---

# Railway Deployment

## Prerequisites

- [Railway CLI](https://docs.railway.com/cli#installing-the-cli) installed
- Logged in via `railway login`
- `OPENAI_API_KEY` set in `.env.production` (or `.env`)

## Deploy Scripts

| Script | Purpose |
|--------|---------|
| `scripts/railway/up.sh` | First-time provisioning — creates project, SurrealDB, app service |
| `scripts/railway/env-sync.sh` | Syncs env vars from `.env.production` to Railway |
| `scripts/railway/redeploy.sh` | Redeploys app service after code changes |

## First-Time Deploy

```bash
./scripts/railway/up.sh
```

This provisions:
1. A Railway project named `agent-platform`
2. A SurrealDB database service (`surrealdb/surrealdb:latest`)
3. An `agent-os` app service with essential env vars

## Your First Deploy Will Fail (by Design)

JWT auth is on by default (`authorization=True` when `RUNTIME_ENV=prd`). Without `JWT_VERIFICATION_KEY`, the app refuses to serve traffic.

### Get Your Verification Key

1. Open [os.agno.com](https://os.agno.com), click **Add OS** → **Live**, enter your Railway domain, and connect.
2. Enable **Token Based Authorization**.
3. Copy the public key (full PEM block).

### Set Production Env

```bash
cp .env .env.production
```

Edit `.env.production`:

```ini
JWT_VERIFICATION_KEY=-----BEGIN PUBLIC KEY-----
MIIBIjANBgkq...
-----END PUBLIC KEY-----

AGENTOS_URL=https://<your-app>.up.railway.app
```

### Sync and Deploy

```bash
./scripts/railway/env-sync.sh
```

Railway auto-deploys when env values change. Watch the logs:

```bash
railway logs --service agent-os
```

## Redeploy After Code Changes

```bash
./scripts/railway/redeploy.sh
```

For auto-deploy on push to `main`: connect your repo in Railway dashboard → agent-os service → Settings → Source → Connect Repo.

## Environment Variables

| Variable | Required | Default | Notes |
|----------|----------|---------|-------|
| `OPENAI_API_KEY` | yes | — | Models + embeddings |
| `JWT_VERIFICATION_KEY` | prd | — | PEM block from os.agno.com |
| `AGENTOS_URL` | no | `http://127.0.0.1:8000` | Set to Railway domain for scheduler |
| `PARALLEL_API_KEY` | no | — | WebSearch agent auth |
| `SLACK_BOT_TOKEN` / `SLACK_SIGNING_SECRET` | no | — | Both required for Slack |
| `SURREALDB_URL` | no | `ws://surrealdb.railway.internal:8000` | Set by `up.sh` |
| `SURREALDB_USER` / `SURREALDB_PASS` | no | `root` | Set by `up.sh` |
| `SURREALDB_NAMESPACE` / `SURREALDB_DATABASE` | no | `agno` / `agentos` | Set by `up.sh` |
| `PORT` | no | `8000` | Railway sets this automatically |

## Troubleshooting

### Deploy fails immediately

Check the logs:

```bash
railway logs --service agent-os
```

Common causes:
- **Missing `JWT_VERIFICATION_KEY`** — set it in `.env.production` and run `env-sync.sh`
- **Missing `OPENAI_API_KEY`** — add to `.env.production` and sync
- **Build failure** — check `Dockerfile` and `requirements.txt` are valid

### App starts but returns 401

JWT auth is rejecting requests. Either:
- Set `JWT_VERIFICATION_KEY` correctly (full PEM, no surrounding quotes)
- Or set `authorization=False` in `app/main.py` (not recommended for production)

### Database connection errors

Verify the `SURREALDB_URL` is `ws://surrealdb.railway.internal:8000` (Railway's internal DNS for linked services). The `up.sh` script sets this automatically.

### Scheduler not triggering

Ensure `AGENTOS_URL` is set to your public Railway domain (e.g. `https://my-app.up.railway.app`). The scheduler needs a reachable URL for cron callbacks.

### Scaling

Default: 2 replicas, 4Gi memory, 2 vCPU. Adjust in `railway.json`:

```json
{
  "deploy": {
    "numReplicas": 2,
    "limits": {
      "cpu": 2000,
      "memory": "4Gi"
    }
  }
}
```

### Opting Out of JWT

Set `authorization=False` in `app/main.py` and redeploy. Only do this inside a private VPC behind another auth layer.
