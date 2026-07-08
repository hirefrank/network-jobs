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

Read [SCHEMA.md](../SCHEMA.md) first. For category mapping details see [reference.md](reference.md).

## Configuration

- **DATA**: `NETWORK_JOBS_HOME` or `~/.network-jobs`
- **Never** fetch `https://jobs.hirefrank.com` — that hosted export is retired for this suite.

```bash
DATA="${NETWORK_JOBS_HOME:-$HOME/.network-jobs}"
cat "$DATA/profile.json"
cat "$DATA/corpus/manifest.json"
```

## Data files

| File | Purpose |
|------|---------|
| `profile.json` | Search header + intro footer identity |
| `corpus/manifest.json` | Category index + granular file map |
| `corpus/{category}.json` | Full category list |
| `corpus/{category}-{loc}-{seniority}.json` | Preferred granular shards |
| `companies/companies.json` | Connection graph (for “who do I know?”) |

**Location buckets:** `nyc`, `sf`, `remote`, `other`  
**Seniority buckets:** `senior`, `mid`  
**Categories:** see reference.md

## Procedures

**First step for all patterns:** load profile + manifest.

```bash
DATA="${NETWORK_JOBS_HOME:-$HOME/.network-jobs}"
jq -r '"\(.name)|\(.title)|\(.company)|\(.email)"' "$DATA/profile.json"
jq . "$DATA/corpus/manifest.json"
```

If `manifest.totalJobs` is 0 or `lastUpdated` is null, tell the user to run **careers-discover** + **jobs-ingest** first (and **network-jobs-import** if companies are empty).

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

- **careers-discover** / **jobs-ingest** — refresh local openings
- **intro-email-generator** — draft forwardable warm intro (pass job URL + forwarder name + resume)
- **network-jobs-import** — refresh LinkedIn graph
