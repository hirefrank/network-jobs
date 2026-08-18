---
name: network-jobs-import
description: Import a LinkedIn connections ZIP into the local Network Jobs graph. Use when the user provides a LinkedIn data export ZIP or Connections.csv and wants companies/people available for careers discovery.
license: MIT
allowed-tools: Bash(*)
metadata:
  version: "1.0.0"
---

# Network Jobs Import

Turn a LinkedIn connections export into local `connections.json` + `companies.json`.

Read [SCHEMA.md](../SCHEMA.md) first.

## Inputs

- Path to LinkedIn ZIP (preferred) or a bare `Connections.csv`
- Optional: `--min-count N` (default 1) — drop companies with fewer than N connections when summarizing

## Workflow

1. **Confirm data home** — `NETWORK_JOBS_HOME` or `~/.network-jobs/`.
2. **Run the parser** (deterministic — do not reimplement CSV parsing in prose):

```bash
HELPER="$(dirname "$0")/helpers/parse-linkedin.sh"
# When invoked via skill symlink, resolve suite helper:
HELPER="${NETWORK_JOBS_SUITE:-$HOME/.claude/skills/network-jobs-suite}/network-jobs-import/helpers/parse-linkedin.sh"
DATA="${NETWORK_JOBS_HOME:-$HOME/.network-jobs}"

"$HELPER" "/path/to/linkedin.zip" --out "$DATA"
```

3. **Report**
   - Total connections kept
   - Companies after ignore-list filtering
   - Top 15 companies by connection count (name + count + sample people)
4. **Optional fuzzy merge** — If the user asks, or obvious duplicates appear (e.g. “Meta” / “Facebook”), propose merges and write overrides to `$DATA/config/company-overrides.json` as `{ "linkedinName": "...", "matchTo": "..." }`, then re-run the helper.
5. **Hand off** — Suggest `careers-discover` on top companies by count.

## Helper behavior

`helpers/parse-linkedin.sh`:

- Extracts `Connections.csv` from ZIP (or reads CSV directly)
- Skips LinkedIn note preamble; finds header with First Name + Company
- Applies ignore lists from `$DATA/config/` (seeded from `assets/` on setup)
- Applies company-overrides
- Writes:
  - `$DATA/connections/connections.json`
  - `$DATA/companies/companies.json`
  - `$DATA/logs/import-<timestamp>.json` summary

## Non-negotiables

- Do not upload the ZIP or CSV anywhere.
- Do not invent companies or people not in the file.
- Prefer the helper over ad-hoc Python/Node one-offs unless the helper fails — then fix/extend the helper.
