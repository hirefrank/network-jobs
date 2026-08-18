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

Read [SCHEMA.md](../../SCHEMA.md) first.

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
4. **Merge** into corpus via helper (required):
   - Write the **new/updated jobs only** to a working file (e.g. `$DATA/corpus/.work/batch.json`)
   - Run [`helpers/rebuild-corpus.sh`](helpers/rebuild-corpus.sh) on that file
   - The helper **merges by URL** with existing `corpus/jobs-all.json` (incoming wins), rewrites shards + manifest, and **deletes stale shard files**
   - Do **not** pass a partial list as if it were the full corpus — merge is automatic
5. **Report** incoming count, total after merge, removed stale shards; show `manifest.totalJobs` and `lastUpdated`
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
SUITE="$(cat "$DATA/suite-root" 2>/dev/null || true)"
SUITE="${NETWORK_JOBS_SUITE:-${SUITE:-}}"
# After normalizing a triage batch to $DATA/corpus/.work/batch.json:
"$SUITE/skills/jobs-ingest/helpers/rebuild-corpus.sh" "$DATA/corpus/.work/batch.json"
# Or, from this skill's own helpers/ when the skill dir is on disk:
# ./helpers/rebuild-corpus.sh "$DATA/corpus/.work/batch.json"
```

The helper merges by URL with existing `corpus/jobs-all.json`, shards by category/location/seniority, rewrites `manifest.json`, and removes stale shard files.

## Related

- Upstream: **careers-discover**
- Downstream search: **network-jobs**
