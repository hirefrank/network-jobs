# Network Jobs

Local-first Claude Code skill suite: import your LinkedIn connections, discover company career pages, build a personal job corpus, search openings, and draft warm intros — all on your machine.

No Cloudflare Workers. No hosted job DB. No ATS adapter matrix. The model finds career pages and extracts listings; optional recipes cache hard-won site knowledge.

## Install

```bash
git clone --depth 1 https://github.com/hirefrank/network-jobs.git ~/.claude/skills/network-jobs-suite \
  && cd ~/.claude/skills/network-jobs-suite && ./setup
```

Clone as **`network-jobs-suite`**, not `network-jobs` — that name is reserved for the search skill symlink `./setup` creates.

Requires: `curl`, `jq`, `unzip`. Recommended: [`agent-browser`](https://github.com/vercel-labs/agent-browser) for JS-heavy career sites.

`./setup` will:

1. Create `~/.network-jobs/` (connections, companies, triage, corpus, logs)
2. Symlink each skill into `~/.claude/skills/` (including `network-jobs` → suite/`network-jobs/`)
3. Print a CLAUDE.md routing snippet to paste into your project

Override paths with `NETWORK_JOBS_HOME` and `NETWORK_JOBS_SKILLS_DIR` if needed.

## Pipeline

```text
LinkedIn ZIP
    → network-jobs-import   (connections + companies graph)
    → careers-discover      (stage openings under triage/)
    → jobs-ingest           (promote to corpus/ after you confirm)
    → network-jobs          (search local corpus)
    → intro-email-generator (forwardable warm intro)
```

Always read [SCHEMA.md](SCHEMA.md) for paths and JSON shapes.

## Quick start

1. **Export LinkedIn connections**  
   LinkedIn → Settings → Data privacy → Get a copy of your data → select **Connections** → download ZIP when ready.

2. **Setup + import** (in Claude Code)  
   - “Set up network jobs” → fill `profile.json`  
   - “Import my LinkedIn zip at ~/Downloads/Connections.zip”

3. **Discover + ingest**  
   - “Find open roles at my top 5 companies by connection count”  
   - Review triage `INVENTORY.md`, then “ingest the Stripe triage batch”

4. **Search + intro**  
   - “Find senior PM roles in NYC in my network”  
   - “Draft an intro to Jane for the Stripe PM role” (have resume ready)

## Skills

| Skill | Role |
|-------|------|
| [`network-jobs-setup`](network-jobs-setup/SKILL.md) | First-run profile + LinkedIn export help |
| [`network-jobs-import`](network-jobs-import/SKILL.md) | ZIP → local company graph |
| [`careers-discover`](careers-discover/SKILL.md) | Model-driven career page discovery + staging |
| [`jobs-ingest`](jobs-ingest/SKILL.md) | Triage → normalized corpus shards |
| [`network-jobs`](network-jobs/SKILL.md) | Search / list openings from local corpus |
| [`intro-email-generator`](intro-email-generator/SKILL.md) | Forwardable warm intro emails |

## Design notes

- **Provenance-style scraping:** orchestration skills + optional `careers-discover/references/` recipes. No Greenhouse/Lever/Ashby TypeScript parsers.
- **Staging gate:** discover never writes the corpus; ingest waits for your confirm.
- **PII stays local:** `~/.network-jobs/` is gitignored from this repo’s perspective — never commit your connections.

## Fixtures

`fixtures/Connections.csv` is a tiny LinkedIn-shaped export for local testing:

```bash
export NETWORK_JOBS_HOME=/tmp/nj-test
./setup   # or mkdir -p $NETWORK_JOBS_HOME/{connections,companies,config,logs}
./network-jobs-import/helpers/parse-linkedin.sh ./fixtures/Connections.csv
```

## Decommissioning the old Workers app

See [docs/DECOMMISSION.md](docs/DECOMMISSION.md). Keep `apps/jobs` running until this suite is your daily driver.

## License

MIT
