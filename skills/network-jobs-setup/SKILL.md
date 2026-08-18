---
name: network-jobs-setup
description: First-run setup for the local Network Jobs suite. Use when installing network jobs, filling profile.json, verifying ~/.network-jobs, or helping the user export LinkedIn connections.
license: MIT
metadata:
  version: "1.0.0"
---

# Network Jobs Setup

Onboard a user onto the local Network Jobs suite. No cloud account.

Always read [SCHEMA.md](../../SCHEMA.md) first.

## Data home

`NETWORK_JOBS_HOME` or `~/.network-jobs/`.

## Workflow

1. **Verify install**
   - Confirm suite skills are discoverable (`network-jobs-import`, `careers-discover`, `jobs-ingest`, `network-jobs`, `intro-email-generator`).
   - If missing, tell the user to run:
     ```bash
     npx skills add hirefrank/network-jobs -g -a claude-code -a cursor -a codex
     npx --yes 'github:hirefrank/network-jobs#main' setup --agent auto
     ```
     or `network-jobs setup --agent auto` / `network-jobs doctor`.
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

4. **Hand off + tips**
   Tell the user to run **network-jobs-import** with the ZIP path, e.g.  
   “Import my LinkedIn zip at ~/Downloads/Basic_LinkedInDataExport_….zip”

   Then surface this short tips block (paraphrase fine; keep it model-agnostic):

   ```text
   Tips
   - Pipeline: import → careers-discover (stages only) → you confirm → jobs-ingest → search → warm intro.
   - Discovery (career pages) benefits from a stronger model; local search / intros are fine on a mid-tier model.
   - After discover finishes, review triage/ — do not ingest until you say so.
   - Refresh the suite: network-jobs update
   - Health check: network-jobs doctor
   ```

## Checks

```bash
DATA="${NETWORK_JOBS_HOME:-$HOME/.network-jobs}"
ls -la "$DATA"
cat "$DATA/profile.json"
command -v curl jq unzip
command -v agent-browser || echo "agent-browser missing — network-jobs update"
command -v network-jobs || echo "network-jobs CLI missing — re-run setup"
```

## Non-negotiables

- Never send profile or connections to a remote API.
- Never create a hosted account or fetch a remote job export; this suite is local-only.
- Do not name a specific model vendor or product when giving tips — stay model-agnostic.
