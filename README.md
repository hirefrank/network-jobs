# Network Jobs

Local-first agent skill suite: import your résumé and preferences, import LinkedIn connections, discover company career pages, build a personal job corpus, search openings, and draft warm intros — on your machine.

Works with any agent that loads [Agent Skills](https://agentskills.io) (Claude Code, Cursor, Codex, OpenCode, Pi, and others).

## Install

```bash
npx --yes 'github:hirefrank/network-jobs#main' setup --agent auto
```

This creates `~/.network-jobs/`, installs `agent-browser` when missing, puts `network-jobs` on PATH (`~/.local/bin`), and symlinks all six skills into each detected agent’s skills directory.

```bash
network-jobs setup --agent claude-code,cursor,codex
network-jobs setup --agent all
network-jobs setup --force          # replace skill dirs from an older install
network-jobs setup --no-browser     # skip agent-browser install
network-jobs setup -v               # print every path
network-jobs update                 # fetch latest + relink
network-jobs doctor
```

Requires: `curl`, `jq`, `unzip`, `python3`, and a working `npm` (for [`agent-browser`](https://github.com/vercel-labs/agent-browser)). Optional: `pdftotext` for PDF résumé extraction.

Optional alternate skill placement: `npx skills add hirefrank/network-jobs -g -a …` then still run `network-jobs setup` for data + launcher.

### Then use your agent

- “Set up network jobs from my resume” → profile + **dynamic** preferences interview  
- “Import my LinkedIn zip at ~/Downloads/….zip”  
- “Find open roles at my top companies” → review triage → “ingest that batch”  
- “Senior PM jobs in NYC” → “Draft an intro to Jane”

Daily use is **in the agent**. The CLI is for install, update, doctor, résumé/LinkedIn import, and corpus clear.

## Tips

- **Pipeline stop:** `careers-discover` only stages under `triage/`. Review, then explicitly ask to ingest.
- **Résumé + prefs:** `network-jobs profile import ~/resume.pdf`, then in your agent run setup from the résumé. Interview covers remote/hybrid/onsite (**onsite scoped to specific cities**, not every office), location, IC vs manager, **former employers include/exclude**, stage/domain, and other gaps the résumé implies.
- **Model choice (agnostic):** prefer a **stronger** model for career-page discovery; mid-tier is usually enough for local search and intro drafts.
- **Refresh:** `network-jobs update`
- **Health:** `network-jobs doctor`
- **Data:** everything under `~/.network-jobs/` — no hosted API.

## Pipeline

```text
Résumé
    → profile import + setup skill   (profile.json + preferences.json)
LinkedIn ZIP
    → network-jobs-import            (connections + companies graph)
    → careers-discover               (stage openings under triage/)
    → you confirm
    → jobs-ingest                    (promote to corpus/)
    → network-jobs                   (search local corpus using prefs defaults)
    → intro-email-generator          (forwardable warm intro; uses local résumé)
```

Always read [SCHEMA.md](SCHEMA.md) for paths and JSON shapes.

## Quick start

1. **Install** — `npx --yes 'github:hirefrank/network-jobs#main' setup --agent auto`

2. **Résumé**

```bash
network-jobs profile import ~/Downloads/Resume.pdf
```

Then in your agent: “set up network jobs from my resume” (profile + prefs, including whether to consider roles at former employers).

3. **LinkedIn connections**  
   Settings → Data privacy → Get a copy of your data → **Connections** → download ZIP.

```bash
network-jobs import ~/Downloads/Connections.zip
```

4. **Discover + ingest** in the agent  
   “Find open roles at my top 5 companies” → review triage → “ingest the Stripe batch”

5. **Search + intro** in the agent  
   “Find senior PM roles in NYC” → “Draft an intro to …”

## Skills

| Skill | Role |
|-------|------|
| [`network-jobs-setup`](skills/network-jobs-setup/SKILL.md) | Résumé → profile, preferences interview, LinkedIn export help |
| [`network-jobs-import`](skills/network-jobs-import/SKILL.md) | ZIP → local company graph |
| [`careers-discover`](skills/careers-discover/SKILL.md) | Model-driven career page discovery + staging |
| [`jobs-ingest`](skills/jobs-ingest/SKILL.md) | Triage → normalized corpus shards (after you confirm) |
| [`network-jobs`](skills/network-jobs/SKILL.md) | Search local corpus (prefs as defaults) |
| [`intro-email-generator`](skills/intro-email-generator/SKILL.md) | Forwardable warm intro emails |

## CLI

```bash
network-jobs setup | update | doctor | which | agents | routing
network-jobs import <zip-or-csv>
network-jobs profile import <resume-file>
network-jobs profile show
network-jobs corpus clear [--triage] [--yes]
network-jobs reset [--data] [--purge-cache] [--yes]
network-jobs uninstall [--yes]    # alias for reset --data
```

Skills self-describe for routing. `network-jobs routing` prints an optional snippet for a project instruction file.

## Design notes

- **Provenance-style scraping:** orchestration + optional recipes — no ATS adapter matrix.
- **Shared data:** one `~/.network-jobs/` for every agent on the machine.
- **Symlink installs:** one suite copy; `update` re-points agent skill links.
- **Prefs-aware discovery/search:** former employers and other interview fields shape defaults; the user’s query always wins.

## Fixtures

```bash
export NETWORK_JOBS_HOME=/tmp/nj-test
npx --yes 'github:hirefrank/network-jobs#main' setup --agent auto --no-browser
npx --yes 'github:hirefrank/network-jobs#main' import ./fixtures/Connections.csv
```

## Decommissioning the old Workers app

See [docs/DECOMMISSION.md](docs/DECOMMISSION.md).

## License

MIT
