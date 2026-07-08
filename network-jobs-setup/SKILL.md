---
name: network-jobs-setup
description: First-run setup for the local Network Jobs suite. Use when installing network jobs, filling profile.json, verifying ~/.network-jobs, or helping the user export LinkedIn connections.
license: MIT
metadata:
  version: "1.0.0"
---

# Network Jobs Setup

Onboard a user onto the local Network Jobs suite. No cloud account.

Always read [SCHEMA.md](../SCHEMA.md) first.

## Data home

`NETWORK_JOBS_HOME` or `~/.network-jobs/`.

## Workflow

1. **Verify install**
   - Confirm suite skills are discoverable (`network-jobs-import`, `careers-discover`, `jobs-ingest`, `network-jobs`, `intro-email-generator`).
   - If missing, tell the user to run `./setup` from the suite clone (see README).
   - Confirm dirs exist: `connections/`, `companies/`, `triage/`, `corpus/`, `config/`, `logs/`.

2. **Fill profile.json**
   Ask for (or infer from conversation):
   - `name` (required for search header / intro footer)
   - `email` (required for intro handoff footer)
   - `title`, `company`, `url` (optional)

   Write `~/.network-jobs/profile.json`. Do not invent an email.

3. **LinkedIn export instructions**
   Guide the user:

   1. Open LinkedIn → **Settings & Privacy** → **Data privacy** → **Get a copy of your data**
   2. Select **Connections** only (faster than full archive)
   3. Request archive; wait for LinkedIn email
   4. Download the ZIP (contains `Connections.csv`)

4. **Hand off**
   Tell the user to run **network-jobs-import** with the ZIP path, e.g.  
   “Import my LinkedIn zip at ~/Downloads/Basic_LinkedInDataExport_….zip”

## Checks

```bash
DATA="${NETWORK_JOBS_HOME:-$HOME/.network-jobs}"
ls -la "$DATA"
cat "$DATA/profile.json"
command -v curl jq unzip
command -v agent-browser || echo "agent-browser optional"
```

## Non-negotiables

- Never send profile or connections to a remote API.
- Never create a hosted advisor slug or curl `jobs.hirefrank.com`.
