---
name: careers-discover
description: Find company career pages and stage open job listings into local triage for Network Jobs. Use when discovering openings at companies from the user's LinkedIn graph — no ATS adapters; the model finds and extracts.
license: MIT
allowed-tools: Bash(*)
metadata:
  version: "1.0.0"
---

# Careers Discover

Orchestration only: discover a company's careers surface, extract open roles, stage under `triage/`. Does **not** write the corpus — that is `jobs-ingest` after user confirmation.

Read [SCHEMA.md](../SCHEMA.md) first. Pattern inspired by Provenance `source-scrape`.

## When to use

- User wants openings at companies from `~/.network-jobs/companies/companies.json`
- User names companies to refresh
- User asks to “crawl” / “find jobs at …” their network

## Non-negotiables

- Stage everything under `triage/careers-<slug>-<YYYY-MM-DD>/` — never write `corpus/` from this skill.
- Do **not** invent titles, salaries, or dates. Omit unknown fields.
- Write fetch-log entries **before** summarizing results to the user.
- No ATS allowlist / no Greenhouse-Lever-Ashby parser code. Prefer whatever public page or JSON the site exposes.
- One company (or small batch the user approved) per focused run when possible — cleaner logs.

## Workflow

1. **Pick companies**
   - Read `$DATA/companies/companies.json`
   - Prefer high `connectionCount`, or filter by user query
   - Ask before bulk-running more than ~5 companies in one go

2. **Check recipes**
   - Look in this skill’s [`references/`](references/) for a matching company or site-family recipe
   - If none exists and the site is painful, draft one from [`references/_template.md`](references/_template.md) **with the user** before scaling

3. **Discover careers URL** (in order)
   1. Known `domain` on the company record, try `/careers`, `/jobs`, `/careers/openings`, `/join`
   2. Web search: `"{company}" careers` / `"{company}" jobs`
   3. Company homepage → follow Careers/Jobs nav
   4. If blocked or SPA-only → `agent-browser` (snapshot → refs)
   5. If still blocked → ask user to save/share the page (CDP / manual capture)

4. **Extract listings**
   - Prefer structured JSON if the page or network tab exposes a jobs API
   - Else parse visible listing cards / table rows
   - For each role capture: `title`, `url` (required), `location`, `department`, `salary` (only if shown), `postedAt` (only if shown), `sourceUrl`
   - Follow pagination / “Load more” when practical; note caps in INVENTORY

5. **Stage**

```text
$DATA/triage/careers-<slug>-<YYYY-MM-DD>/
├── INVENTORY.md
├── index/listings.json
└── fetch-log/<timestamp>-<label>.json
```

Use [`helpers/stage-company.sh`](helpers/stage-company.sh) to mkdir + write skeleton files, then fill listings.

6. **INVENTORY.md must include**
   - Company name + slug
   - Careers URL(s) used
   - Listing count
   - Connections at company (from graph) + sample people
   - Caveats (bot wall, partial pagination, uncertain domain)
   - Next steps (“ready for jobs-ingest?” / “need recipe”)

7. **Hand off**
   - Point at the triage dir
   - Ask whether to run `jobs-ingest` on this batch

## Bot / fetch tiers

1. Public `curl` / WebFetch (static HTML or public JSON)
2. `agent-browser` headed/headless automation
3. User real-browser / CDP capture promoted into triage

## Helpers

- [`helpers/stage-company.sh`](helpers/stage-company.sh) — create triage dir skeleton
- [`helpers/fetch-page.sh`](helpers/fetch-page.sh) — curl page to fetch-log + stdout path

## Related

- After confirm → **jobs-ingest**
- Search corpus → **network-jobs**
