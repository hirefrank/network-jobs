---
name: jobs-ingest
description: Promote Network Jobs triage batches into the local searchable corpus. Use ONLY after the user explicitly confirms a triage folder should be ingested — never auto-chain from careers-discover.
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

- Confirmation looks like: “ingest these”, “ingest matches”, “ingest all”, “promote the Slack batch”, “yes, put them in the corpus”.
- Default ingest set is **matches** (`index/matches.json`) when present. “ingest all” uses `listings.json`. A department name slices whichever set you chose.
- Not confirmation: the user earlier saying “run careers-discover”, finishing background agents, or you planning a full pipeline.
- If unsure, list staged dirs + listing counts and ask.

## Workflow

1. **Select triage dir(s)** under `$DATA/triage/careers-*`
2. **Choose the ingest set** (user query wins; otherwise **matches**):
   - Default / “ingest these” / “ingest matches” → `index/matches.json` (`.jobs`)
   - “ingest all” → `index/listings.json`
   - “ingest Product” / a department name → filter that set by `department`
   - If `matches.json` is missing, fall back to `listings.json` and say so
3. **Read** the chosen listings + `INVENTORY.md` (quote **N of M match prefs**, not the raw board)
4. **Normalize each listing** into a corpus job object:
   - `id` — stable slug: `{companySlug}-{title-slug}-{fingerprint-tail}`
   - `fingerprint` — ATS `externalId` or company+normalized title+locations (not URL)
   - `company` / `companyDomain` — from company graph + discovery notes
   - `category` — map title/department to one of the 15 categories (model judgment; see network-jobs reference)
   - `location` plus `locations[]` when the posting names more than one office
   - `locationBucket` — `nyc` | `sf` | `remote` | `other`
   - `seniority` — `senior` if title matches Senior/Staff/Principal/Lead/Director/VP/Head; else `mid`
   - `status` — `open` (re-open if a previously closed fingerprint returns)
   - `firstSeen` / `lastSeen` — today (ISO date) if new; bump `lastSeen` if fingerprint already in corpus
   - Keep `salary` / `postedAt` only if present in triage
5. **Merge** into corpus via helper (required):
   - Write the **new/updated jobs only** to a working file (e.g. `$DATA/corpus/.work/batch.json`)
   - Read `index/pagination.json` (or INVENTORY). Pass `--pagination-complete` **only** when `complete` is true.
   - Run [`helpers/rebuild-corpus.sh`](helpers/rebuild-corpus.sh) on that file:

```bash
"$SUITE/skills/jobs-ingest/helpers/rebuild-corpus.sh" "$DATA/corpus/.work/batch.json" \
  --expire-company "$SLUG" --pagination-complete    # only if pagination.complete
# or, when truncated / incomplete:
"$SUITE/skills/jobs-ingest/helpers/rebuild-corpus.sh" "$DATA/corpus/.work/batch.json" \
  --expire-company "$SLUG" --pagination-incomplete
```

   - The helper **merges by fingerprint** with existing `corpus/jobs-all.json` (incoming wins, `firstSeen` kept), rewrites shards + manifest, and **deletes stale shard files**
   - Unseen jobs for that company are marked `closed` **only** when `--pagination-complete` is set. Never expire on incomplete crawls.
   - Do **not** pass a partial list as if it were the full corpus — merge is automatic; expiry uses the incoming fingerprint set as “seen”
6. **Report** incoming count, total after merge, removed stale shards; show `manifest.totalJobs` and `lastUpdated`
7. Leave triage dirs in place (do not delete unless user asks)

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
"$SUITE/skills/jobs-ingest/helpers/rebuild-corpus.sh" "$DATA/corpus/.work/batch.json" \
  --expire-company "$SLUG" --pagination-complete   # only if pagination.complete
```

The helper merges by fingerprint with existing `corpus/jobs-all.json`, shards by category/location/seniority, rewrites `manifest.json`, removes stale shard files, and closes unseen jobs for `--expire-company` **only** when `--pagination-complete` is set.

## Related

- Upstream: **careers-discover**
- Downstream search: **network-jobs**
