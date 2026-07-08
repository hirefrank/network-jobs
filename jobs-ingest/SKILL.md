---
name: jobs-ingest
description: Promote Network Jobs triage batches into the local searchable corpus. Use after careers-discover when the user confirms a triage folder should be ingested.
license: MIT
allowed-tools: Bash(*)
metadata:
  version: "1.0.0"
---

# Jobs Ingest

Normalize staged listings → `~/.network-jobs/corpus/` shards + `manifest.json`.

Read [SCHEMA.md](../SCHEMA.md) first.

## Gate

**Do not ingest without explicit user confirmation** for the triage path(s).

## Workflow

1. **Select triage dir(s)** under `$DATA/triage/careers-*`
2. **Read** `index/listings.json` + `INVENTORY.md`
3. **Normalize each listing** into a corpus job object:
   - `id` — stable slug: `{companySlug}-{title-slug}-{hash-of-url}`
   - `company` / `companyDomain` — from company graph + discovery notes
   - `category` — map title/department to one of the 15 categories (model judgment; see network-jobs reference)
   - `locationBucket` — `nyc` | `sf` | `remote` | `other`
   - `seniority` — `senior` if title matches Senior/Staff/Principal/Lead/Director/VP/Head; else `mid`
   - `firstSeen` / `lastSeen` — today (ISO date) if new; bump `lastSeen` if URL already in corpus
   - Keep `salary` / `postedAt` only if present in triage
4. **Merge** into corpus:
   - Prefer helper: [`helpers/rebuild-corpus.sh`](helpers/rebuild-corpus.sh) after writing/updating a working `jobs-all.json`, **or**
   - Update category files + granular `{category}-{loc}-{seniority}.json` + `manifest.json` carefully with jq
5. **Report** counts added/updated/skipped; show new `manifest.totalJobs` and `lastUpdated`
6. Leave triage dirs in place (do not delete unless user asks)

## Categories

`engineering` | `product` | `design` | `data` | `ai-ml` | `sales` | `marketing` | `customer-success` | `operations` | `finance` | `people` | `legal` | `it-security` | `retail` | `other`

## Location heuristics

- NYC / New York / Brooklyn / Manhattan → `nyc`
- SF / San Francisco / Bay Area / Palo Alto / Mountain View / Oakland → `sf`
- Remote / Distributed / Work from home → `remote`
- else → `other`

## Helper

```bash
DATA="${NETWORK_JOBS_HOME:-$HOME/.network-jobs}"
# After producing $DATA/corpus/.work/jobs-all.json (array of normalized jobs):
"$SUITE/jobs-ingest/helpers/rebuild-corpus.sh" "$DATA/corpus/.work/jobs-all.json"
```

The helper shards by category/location/seniority and rewrites `manifest.json`.

## Related

- Upstream: **careers-discover**
- Downstream search: **network-jobs**
