---
name: network-jobs
description: Find jobs where you're already connected. Search openings in your local Network Jobs corpus at companies from your LinkedIn graph. Use when searching for jobs, checking company connections, or exploring career opportunities.
license: MIT
allowed-tools: Bash(*)
metadata:
  version: "3.0.0"
---

# Network Jobs

Search job openings at companies where you have connections — from your **local** corpus under `~/.network-jobs/`.

Read [SCHEMA.md](../../SCHEMA.md) first. For category mapping details see [reference.md](reference.md).

## Configuration

- **DATA**: `NETWORK_JOBS_HOME` or `~/.network-jobs`
- This suite has **no hosted API**. Every read is a local file; never fetch a remote job export.

```bash
DATA="${NETWORK_JOBS_HOME:-$HOME/.network-jobs}"
cat "$DATA/profile.json"
cat "$DATA/corpus/manifest.json"
```

## Data files

| File | Purpose |
|------|---------|
| `profile.json` | Search header + intro footer identity |
| `preferences.json` | Default work mode, locations, categories, seniority |
| `resume/text.md` | Résumé text for intros / profile fill |
| `corpus/manifest.json` | Category index + granular file map |
| `corpus/{category}.json` | Full category list |
| `corpus/{category}-{loc}-{seniority}.json` | Preferred granular shards |
| `companies/companies.json` | Connection graph (for “who do I know?”) |

**Location buckets:** `nyc`, `sf`, `remote`, `other`  
**Seniority buckets:** `senior`, `mid`  
**Categories:** see reference.md

## Procedures

**First step for all patterns:** load profile + preferences + manifest.

```bash
DATA="${NETWORK_JOBS_HOME:-$HOME/.network-jobs}"
jq -r '"\(.name)|\(.title)|\(.company)|\(.email)"' "$DATA/profile.json"
jq . "$DATA/preferences.json" 2>/dev/null || echo "(no preferences yet)"
jq . "$DATA/corpus/manifest.json"
```

### Empty / first-run gate (STOP here)

If `companies/companies.json` is missing → run **network-jobs-import** (or ask for a LinkedIn ZIP). Do not invent a graph.

If `profile.json` `name` or `email` is empty → run **network-jobs-setup** (résumé import + profile). Discovery can proceed without a profile; search + intros should not.

If `preferences.json` is missing or `interviewComplete` is not true → offer **network-jobs-setup** preferences interview (location, remote/hybrid/onsite, roles) before broad searches. User can skip and override per query.

If `manifest.totalJobs` is 0 or `lastUpdated` is null:

1. Tell the user the corpus is empty.
2. Offer **careers-discover** only (stage openings under `triage/`).
3. **Do not** chain into **jobs-ingest** yourself. After discovery finishes, stop and show staged triage; wait for explicit “ingest this batch” (or equivalent) before loading **jobs-ingest**.
4. Only after ingest completes, resume search with this skill.

Never say you will “discover then ingest then search” in one uninterrupted pass.

### Apply preferences as defaults

When the user does **not** specify location / mode / seniority / category / track:

1. Read `preferences.json`.
2. Prefer shards matching `locationBuckets` + `seniority` + `categories`.
3. Honor `workModes`: if only `remote`, prefer `locationBucket=remote`; if `hybrid`/`onsite`, still include city buckets they listed.
4. Honor `track` when filtering titles: `manager` → prefer Manager/Director/Head/EM/VP people-lead titles; `ic` → de-prioritize pure people-manager titles unless query asks; `either` → no track filter.
5. Soft-filter with `locations`, `industries`, `companyStages`, `mustHaves`, `dealBreakers`, `notes`, `salaryMin` in judgment — do not invent salary on jobs that lack it.
6. **Former employers:** read `formerEmployers` + `formerEmployerPolicy`.
   - `exclude` — omit those companies from default result sets (still show if the user named the company).
   - `include` — treat like any other company.
   - `ask` — if matches appear, list them separately and ask before emphasizing / expanding.
   Match company names case-insensitively / lightly normalized (ignore Inc, LLC, etc.).
7. If the user query conflicts with prefs, **query wins**.

Mention once when defaults applied: e.g. `Using your prefs: remote + NYC, product, senior IC (excluding former employers)`.

### Pattern A: "Do I have connections at [Company]?"

1. Check `companies/companies.json` for the company (connection count + people)
2. Search corpus files for matching `company` (case-insensitive)
3. Report connections **and** open roles (or “connected but no staged openings yet”)

### Pattern B: "Find me [Role] jobs in [Location]" (PREFERRED)

1. Map role → category, location → bucket, seniority if given
2. Read granular file(s) from manifest `byLocation`
3. Sort by `lastSeen` / `postedAt` descending
4. Output in **strict format** below

### Pattern B2: Broad queries

Ask for role type, location, seniority before loading every shard.

### Pattern C: "What's new?"

Sort preferred category (or ask) by `firstSeen` desc; show latest ~10.

### Pattern D: Remote / location-only

Use `{category}-{location}-senior.json` + `-mid.json`.

### Pattern E: Salary filter

Filter where `salary.min` or `salary.max` meets threshold; skip jobs with no salary.

## Output Format

**STRICT FORMAT REQUIRED** — Do NOT summarize or paraphrase. Do NOT write prose/narrative.

1. Header: `Searching via [Name] ([Title])...` or with `@ [Company]` if set
2. Data freshness: `Data as of [Mon D], [H:MM AM/PM] ([relative] ago)` from `manifest.lastUpdated`
3. Summary line: `X [role] roles in [location]:`
4. Group by company (COMPANY NAME in caps, then `- N roles`)
5. Each job: `• [Title] – [Salary if available], [N]d [↗](url)`
6. Days from `postedAt` else `firstSeen` (`3d`, `14d`, …)
7. Footer: `Want help drafting an intro email?` — if profile has email, include it; also offer connection names from `companies.json` when known

**Example:**

```
Searching via Frank Harris (Executive Coach)...
Data as of Jul 8, 3:00 PM (2h ago)

8 PM roles in NYC:

JUSTWORKS - 5 roles
• Group PM, Growth – 26d [↗](https://example.com/job/1)
• Senior PM, Foundations – $150-180k, 39d [↗](https://example.com/job/2)

Want help drafting an intro email? (profile: frank@example.com)
Connections at Justworks: …
```

**DO NOT:**

- Narrative summaries (“I found 93 roles including…”)
- Omit `[↗](url)` links
- Curl remote job hosts for corpus data

## Related Skills

- **network-jobs-setup** — profile, résumé, preferences interview
- **careers-discover** / **jobs-ingest** — refresh local openings
- **intro-email-generator** — draft forwardable warm intro (pass job URL + forwarder name; résumé from `~/.network-jobs/resume/`)
- **network-jobs-import** — refresh LinkedIn graph
