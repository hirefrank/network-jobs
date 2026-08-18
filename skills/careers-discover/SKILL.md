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

Read [SCHEMA.md](../../SCHEMA.md) first. Pattern inspired by Provenance `source-scrape`.

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
   - If `preferences.json` lists `categories` / `notes`, bias toward matching companies when the user has not named any
   - If `formerEmployerPolicy` is `exclude` (default when set), **skip** companies in `formerEmployers` unless the user explicitly named them
   - If policy is `ask` and a top company is a former employer, call that out and confirm before discovering
   - Ask before bulk-running more than ~5 companies in one go

   High connection counts at former employers are common and **not** automatically a signal to prioritize those companies.

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

7. **Hand off (hard stop)**
   - Point at each triage dir and summarize counts / caveats from `INVENTORY.md`
   - Ask whether to run `jobs-ingest` on this batch
   - **STOP.** Do **not** invoke `jobs-ingest`, rebuild the corpus, or resume a job search in the same turn.
   - Only after the user explicitly confirms (e.g. “ingest these”, “promote the Google batch”) should you load **jobs-ingest**.

## Bot / fetch tiers

Escalate only as far as needed. Prefer the cheapest tier that returns real listings.

### 1. `curl` / WebFetch (default)

Use when:
- The careers URL or a linked jobs JSON returns substantive HTML/JSON (titles + links visible in the body)
- A public jobs API is obvious (`/api/…`, `…/jobs.json`, common ATS JSON feeds)
- You’re probing `/careers`, `/jobs`, or a domain homepage for a careers link

Skip straight past this tier only if you already know the site is a heavy SPA from a recipe or prior fetch-log.

### 2. `agent-browser`

Use when tier 1 yields:
- Empty shell / “enable JavaScript” / framework root with no listings
- Soft bot interstitial or cookie wall that blocks content
- Pagination or filters that require click / “Load more” / infinite scroll
- Client-side routing where listing URLs aren’t discoverable from static HTML

Workflow: open URL → snapshot → interact by refs → re-snapshot after DOM changes → write fetch-log before summarizing.

### 3. User capture / CDP

Use when tier 2 still can’t see listings (hard login, hard captcha, geo block). Ask the user to save/share the page; stage from that capture. Do not invent openings.

### Decision rule

```text
try WebFetch/curl
  → real listings?        stage them
  → empty / JS / challenge?  agent-browser once
  → still blocked?           ask user (stop automating)
```

Never start with agent-browser for a simple static page. Never keep retrying browser against a hard auth wall.

## Helpers

- [`helpers/stage-company.sh`](helpers/stage-company.sh) — create triage dir skeleton
- [`helpers/fetch-page.sh`](helpers/fetch-page.sh) — curl page to fetch-log + stdout path

## Related

- After confirm → **jobs-ingest**
- Search corpus → **network-jobs**
