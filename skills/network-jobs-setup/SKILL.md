---
name: network-jobs-setup
description: First-run setup for the local Network Jobs suite. Use when installing network jobs, importing a résumé into profile, running the job-search preferences interview (location, remote/hybrid/onsite), filling profile.json, verifying ~/.network-jobs, or helping export LinkedIn connections.
license: MIT
metadata:
  version: "1.1.0"
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
   - Confirm dirs exist: `connections/`, `companies/`, `triage/`, `corpus/`, `config/`, `logs/`, `resume/`.

2. **Résumé → profile** (preferred before prefs interview)
   - If the user has a résumé path: run  
     `network-jobs profile import <path>`  
     or [`helpers/import-resume.sh`](helpers/import-resume.sh).
   - Read `$DATA/resume/text.md` when present (else `resume/source.*`).
   - Propose updates to `profile.json`: `name`, `email`, `title`, `company`, `url`.
   - **Do not invent an email.** Only use an address found in the résumé or confirmed by the user.
   - If `profile.json` already has values, show a diff and ask before overwrite.
   - Write `~/.network-jobs/profile.json` after confirmation.

   If there is no résumé yet, ask for name/email/title manually (same fields).

3. **Preferences interview** (after background is known)
   Run a short interview grounded in the résumé/profile. Goal: fill `preferences.json` so later search defaults are useful.

   Ask (adapt wording; skip what the résumé already answers clearly):

   1. **Work mode** — remote, hybrid, and/or onsite? (multi-ok)
   2. **Where** — cities / regions they want (and map to buckets `nyc` | `sf` | `remote` | `other` when clear)
   3. **Roles** — preferred categories from the 15 corpus categories (e.g. product, engineering)
   4. **Seniority** — senior and/or mid
   5. **Compensation** — optional annual USD floor, or skip
   6. **Soft notes** — company stage, industry, travel, visa, “no X”, etc.

   Write `$DATA/preferences.json` per SCHEMA (set `interviewComplete: true`, `updatedAt` ISO UTC).

   **STOP** after writing prefs — summarize them and ask what to do next (import LinkedIn / discover roles / search).

4. **LinkedIn export instructions** (if companies graph empty)
   Guide the user:

   1. Open LinkedIn → **Settings & Privacy** → **Data privacy** → **Get a copy of your data**
   2. Select **Connections** only (faster than full archive)
   3. Request archive; wait for LinkedIn email
   4. Download the ZIP (contains `Connections.csv`)

   Then hand off to **network-jobs-import**.

5. **Tips** (model-agnostic; paraphrase fine)

   ```text
   Tips
   - Pipeline: import → careers-discover (stages only) → you confirm → jobs-ingest → search → warm intro.
   - Discovery benefits from a stronger model; local search / intros are fine on a mid-tier model.
   - After discover finishes, review triage/ — do not ingest until you say so.
   - Résumé: network-jobs profile import ~/path/to/resume.pdf
   - Prefs: re-run this setup skill anytime (“update my job search preferences”).
   - Refresh: network-jobs update · Health: network-jobs doctor
   - Wipe jobs only: network-jobs corpus clear --yes
   ```

## Checks

```bash
DATA="${NETWORK_JOBS_HOME:-$HOME/.network-jobs}"
ls -la "$DATA"
cat "$DATA/profile.json"
cat "$DATA/preferences.json" 2>/dev/null || true
ls -la "$DATA/resume" 2>/dev/null || true
command -v curl jq unzip
command -v agent-browser || echo "agent-browser missing — network-jobs update"
command -v network-jobs || echo "network-jobs CLI missing — re-run setup"
```

## Non-negotiables

- Never send profile, résumé, or connections to a remote API.
- Never create a hosted account or fetch a remote job export; this suite is local-only.
- Do not name a specific model vendor when giving tips — stay model-agnostic.
- Preferences interview comes **after** résumé/background when possible so questions are grounded.
