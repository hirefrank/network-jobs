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
network-jobs setup --with-browser   # also install the optional agent-browser CLI
network-jobs setup --force          # replace skill dirs from an older install
network-jobs setup -v               # print every path
network-jobs doctor
```

Requires: `curl`, `jq`, `unzip`, `python3`.

[`agent-browser`](https://github.com/vercel-labs/agent-browser) is optional and **not** installed by default — it pulls a headless browser, and most career pages parse fine with curl or your agent’s fetch tool. Add it with `--with-browser` (or `npm i -g agent-browser`) if you hit JS-heavy sites.

### Then use your agent

Open Claude Code / Cursor / Codex and talk to it:

- “Set up network jobs” → fill profile  
- “Import my LinkedIn zip at ~/Downloads/….zip”  
- “Find open roles at my top companies”  
- “Senior PM jobs in NYC” → “Draft an intro to Jane”

Daily use is **in the agent**. The CLI is for install, doctor, and optional import.

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
   LinkedIn → Settings → Data privacy → Get a copy of your data → **Connections** → download ZIP.

2. **Import** (CLI or agent)

```bash
npx github:hirefrank/network-jobs import ~/Downloads/Connections.zip
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
network-jobs setup [--agent auto|all|claude-code,cursor,…] [--force] [--with-browser] [-v]
network-jobs doctor
network-jobs import <zip-or-csv>
network-jobs agents
network-jobs routing   # optional AGENTS.md snippet
network-jobs which
```

Each skill carries its own `description`, so agents route to them without extra configuration. If you want the workflow pinned in a project's instructions anyway, `network-jobs routing` prints a snippet for `CLAUDE.md` / `AGENTS.md`.

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
