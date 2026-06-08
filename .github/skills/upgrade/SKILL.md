---
name: upgrade
description: Check for and apply pending TaskFlow schema migrations after pulling a new release.
user-invocable: true
---

# Upgrade TaskFlow schema

Use this command after pulling a new release of TaskFlow to ensure your database schema is up-to-date.

## Steps

1. Call the `upgrade` MCP tool to check for and apply any pending schema migrations.
2. Report the result to the user:
   - If `status` is `"up-to-date"`: tell the user their schema is current, show the current version number.
   - If `status` is `"migrations applied"`: list the migrations that were applied and the new version number.
3. If any migrations were applied, suggest the user run `/pipeline-status` to verify their project data is intact.

## What to tell the user

```
✅ Schema is up-to-date (version X)
```

or

```
🔄 Applied N migration(s):
   - 001_add_cycle_number
   - 002_add_whatever
   Schema version: X → Y

Run /pipeline-status to verify your project data.
```
