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

3. **Preferences interview** (after background is known — **dynamic**)
   Run a short interview **grounded in the résumé/profile**. This is not a fixed form.

   **How to run it**
   1. Skim résumé + current `profile.json`. Note likely track (IC vs manager), domains, seniority signals, recent employers, and gaps.
   2. Propose a **draft prefs summary** from what you already know (“Sounds like senior IC product in fintech/devtools, NYC-leaning…”).
   3. Ask **only the open questions** — skip anything the résumé already settles.
   4. Branch: if they were a manager, ask whether they want to stay on a people-manager track, return to IC, or either; if lifelong IC, ask whether they’re open to managing. Same idea for domain switches, founding vs bigco, etc.
   5. Write `$DATA/preferences.json` (SCHEMA). Set `interviewComplete: true` and `updatedAt`. Extra keys OK when useful.

   **Core dimensions to cover if still unknown** (ask conversationally, not as a checklist dump):

   | Dimension | Examples |
   |-----------|----------|
   | Work mode | remote / hybrid / onsite — and if hybrid/onsite, **where** (never “any office”) |
   | Location | cities → map to `nyc` \| `sf` \| `remote` \| `other` when clear; fill `onsiteLocations` for in-person willingness |
   | Role category | from the 15 corpus categories, biased by résumé |
   | Seniority | senior / mid |
   | Track | `ic` / `manager` / `either` |
   | Company shape | stage, size, industry (from their history + desires) |
   | Former employers | include / exclude / ask — see below |
   | Comp | optional `salaryMin`, or skip |
   | Must-haves / deal-breakers | e.g. no pure people-mgmt, must have eng partnership |

   **Dynamic follow-ups** (pick what fits *this* person):
   - IC ↔ manager trajectory
   - Stay in current domain vs pivot (use résumé industries)
   - Startup vs scale-up vs public
   - Individual contributor craft depth vs broader GM/ops
   - **Former employers** — LinkedIn graphs are dense with connections at places they used to work. From the résumé, list past employers into `formerEmployers`, then ask whether to **include**, **exclude**, or **ask each time** (`formerEmployerPolicy`). Default suggestion: exclude unless they say otherwise.
   - **Onsite scope** — if they want remote *and* are open to onsite/hybrid, ask *which cities/metros* count. Write those to `onsiteLocations` (and matching buckets). Do not interpret “I’ll consider onsite” as every onsite role globally.
   - Travel, visa/work auth, commute limits — only if relevant
   - Anything the résumé makes surprising (“you’ve been EM for 5 years — still want that?”)

   Do **not** ask every dimension every time. Prefer 3–6 tight questions, then confirm the written prefs.

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
