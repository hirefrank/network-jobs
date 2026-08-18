# Network Jobs

Local-first agent skill suite: import LinkedIn connections, discover company career pages, build a personal job corpus, search openings, and draft warm intros — on your machine.

Works with **Claude Code, Cursor, Codex, OpenCode, Pi**, and other agents that load [Agent Skills](https://agentskills.io).

## Install

### Recommended (multi-agent)

```bash
# 1) Install skills into the agents you use
npx skills add hirefrank/network-jobs -g -a claude-code -a cursor -a codex

# 2) Create local data dir + verify
npx github:hirefrank/network-jobs setup --agent auto
# or, after npm i -g @hirefrank/network-jobs:
# network-jobs setup --agent auto
```

Use `--all` with `npx skills` to target every detected agent, or pick agents with `-a`.

### One-shot via this repo’s CLI

```bash
npx github:hirefrank/network-jobs setup --agent auto
```

This creates `~/.network-jobs/` **and** symlinks all six skills into each detected agent’s skills directory.

```bash
network-jobs setup --agent claude-code,cursor,codex
network-jobs setup --agent all
network-jobs setup --force          # replace skill dirs from an older install
network-jobs setup --no-browser     # skip agent-browser install
network-jobs setup -v               # print every path
network-jobs update                 # fetch latest + relink (+ install agent-browser if needed)
network-jobs doctor
```

Requires: `curl`, `jq`, `unzip`, `python3`, and `npm` (to install [`agent-browser`](https://github.com/vercel-labs/agent-browser) for JS-heavy career pages). Setup installs `agent-browser` globally when it is missing; pass `--no-browser` to skip.

### Then use your agent

In any agent that loaded these skills, talk to it in plain language:

- “Set up network jobs from my resume” → profile + preferences interview  
- “Import my LinkedIn zip at ~/Downloads/….zip”  
- “Find open roles at my top companies” → review triage → “ingest that batch”  
- “Senior PM jobs in NYC” → “Draft an intro to Jane”

Daily use is **in the agent**. The CLI is for install, update, doctor, profile/resume import, and optional LinkedIn import.

## Tips

- **Pipeline stop:** `careers-discover` only stages under `triage/`. Review, then explicitly ask to ingest before anything lands in the searchable corpus.
- **Résumé + prefs:** `network-jobs profile import ~/resume.pdf`, then in your agent: “set up network jobs from my resume” — fills profile, then a **dynamic** prefs interview (remote/hybrid/onsite, location, IC vs manager, former employers include/exclude, stage/domain, …) grounded in that background.
- **Model choice (agnostic):** prefer a **stronger** model for career-page discovery and extraction; a mid-tier model is usually enough for local corpus search and intro drafts.
- **Refresh:** `network-jobs update` (or `npx --yes 'github:hirefrank/network-jobs#main' update`) re-fetches main and relinks skills.
- **Health:** `network-jobs doctor` checks tools, PATH, profile, prefs, résumé, skills, and corpus size.
- **Data:** everything lives under `~/.network-jobs/` — no hosted API.

## Pipeline

```text
LinkedIn ZIP
    → network-jobs-import   (connections + companies graph)
    → careers-discover      (stage openings under triage/)
    → you confirm
    → jobs-ingest           (promote to corpus/)
    → network-jobs          (search local corpus)
    → intro-email-generator (forwardable warm intro)
```

Always read [SCHEMA.md](SCHEMA.md) for paths and JSON shapes.

## Quick start

1. **Export LinkedIn connections**  
   LinkedIn → Settings → Data privacy → Get a copy of your data → **Connections** → download ZIP.

2. **Import** (CLI or agent)

```bash
network-jobs import ~/Downloads/Connections.zip
# or ask your agent: import my LinkedIn zip at …
```

3. **Discover + ingest** in the agent  
   “Find open roles at my top 5 companies” → review triage → “ingest the Stripe batch”

4. **Search + intro** in the agent  
   “Find senior PM roles in NYC” → “Draft an intro to …”

## Skills

| Skill | Role |
|-------|------|
| [`network-jobs-setup`](skills/network-jobs-setup/SKILL.md) | First-run profile + LinkedIn export help |
| [`network-jobs-import`](skills/network-jobs-import/SKILL.md) | ZIP → local company graph |
| [`careers-discover`](skills/careers-discover/SKILL.md) | Model-driven career page discovery + staging |
| [`jobs-ingest`](skills/jobs-ingest/SKILL.md) | Triage → normalized corpus shards |
| [`network-jobs`](skills/network-jobs/SKILL.md) | Search local corpus |
| [`intro-email-generator`](skills/intro-email-generator/SKILL.md) | Forwardable warm intro emails |

## CLI

```bash
network-jobs setup [--agent auto|all|claude-code,cursor,…] [--force] [--no-browser] [-v]
network-jobs update [--agent …] [--force] [--no-browser]   # latest main + relink
network-jobs doctor
network-jobs import <zip-or-csv>
network-jobs profile import <resume-file>                 # store résumé for profile + prefs interview
network-jobs profile show
network-jobs corpus clear [--triage] [--yes]              # empty searchable corpus; keep profile/graph
network-jobs reset [--data] [--purge-cache] [--yes]   # remove skill links; --data also wipes ~/.network-jobs
network-jobs uninstall [--yes]                        # alias for reset --data
network-jobs agents
network-jobs routing   # optional AGENTS.md snippet
network-jobs which
```

Each skill carries its own `description`, so agents route to them without extra configuration. If you want the workflow pinned in a project's instructions anyway, `network-jobs routing` prints a snippet you can paste into your agent's instruction file.

To import a résumé and then interview prefs in the agent:

```bash
network-jobs profile import ~/Downloads/Resume.pdf
# then: “set up network jobs from my resume”
```

To empty jobs without wiping your LinkedIn graph:

```bash
network-jobs corpus clear --yes
# or also drop staged batches:
network-jobs corpus clear --triage --yes
```

To refresh an existing install:

```bash
npx --yes 'github:hirefrank/network-jobs#main' update
```

To start over:

```bash
npx --yes 'github:hirefrank/network-jobs#main' uninstall --yes --purge-cache
npx --yes 'github:hirefrank/network-jobs#main' setup --agent auto
```

## Design notes

- **Provenance-style scraping:** orchestration + optional recipes — no ATS adapter matrix.
- **Shared data:** one `~/.network-jobs/` for every agent on the machine.
- **Multi-agent install:** skills CLI places `SKILL.md` folders; our CLI owns data + optional linking.

## Fixtures

```bash
export NETWORK_JOBS_HOME=/tmp/nj-test
npx github:hirefrank/network-jobs setup --agent auto
npx github:hirefrank/network-jobs import ./fixtures/Connections.csv
```

## Decommissioning the old Workers app

See [docs/DECOMMISSION.md](docs/DECOMMISSION.md).

## License

MIT
