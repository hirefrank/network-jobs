# Network Jobs — Local Schema

Operating contract for all skills in this suite. Read this before writing or reading data under `~/.network-jobs/`.

## Data root

Default: `~/.network-jobs/` (override with `NETWORK_JOBS_HOME`).

```text
~/.network-jobs/
├── profile.json
├── preferences.json              # search prefs from agent interview
├── resume/
│   ├── source.<ext>              # original upload (pdf/docx/md/…)
│   └── text.md                   # extracted plain text (when available)
├── connections/
│   └── connections.json
├── companies/
│   └── companies.json
├── config/
│   ├── companies-to-ignore.json      # optional user overrides
│   ├── company-words-to-ignore.json
│   └── company-overrides.json
├── triage/
│   └── careers-<slug>-<YYYY-MM-DD>/
│       ├── INVENTORY.md
│       ├── index/
│       │   ├── listings.json
│       │   ├── matches.json          # prefs-scored shortlist
│       │   ├── pagination.json       # pages / complete / truncated
│       │   └── summary.json
│       └── fetch-log/
│           └── <timestamp>-<label>.json
├── corpus/
│   ├── manifest.json
│   ├── <category>.json
│   └── <category>-<loc>-<seniority>.json
├── search/
│   ├── ranked.json                   # top-K from local ranker
│   └── intros.json                   # 1–2 roles + 1–2 forwarders
└── logs/
    └── setup.log
```

## profile.json

```json
{
  "name": "Frank Harris",
  "email": "frank@example.com",
  "title": "Executive Coach",
  "company": "",
  "url": ""
}
```

Used by `network-jobs` (search header + intro footer) and `intro-email-generator` (job seeker identity when drafting). Prefer filling from a résumé via `network-jobs profile import` + the setup skill — do not invent email.

## preferences.json

Search and discovery defaults from a **résumé-grounded** agent interview (not a fixed questionnaire). Ask only what the background leaves open; skip what the résumé already answers clearly.

```json
{
  "updatedAt": "2026-08-18T23:00:00Z",
  "interviewComplete": true,
  "workModes": ["remote", "hybrid"],
  "locationBuckets": ["nyc", "remote"],
  "locations": ["New York", "Remote US"],
  "onsiteLocations": ["New York"],
  "categories": ["product"],
  "seniority": ["senior"],
  "track": ["ic"],
  "companyStages": ["seed", "series-b", "public"],
  "companySizes": [],
  "industries": ["developer-tools", "fintech"],
  "formerEmployers": ["Acme Corp", "Example Labs"],
  "formerEmployerPolicy": "exclude",
  "salaryMin": null,
  "mustHaves": ["strong eng partnership"],
  "dealBreakers": ["pure people-management with no craft"],
  "notes": "Open to SF onsite for the right role"
}
```

| Field | Meaning |
|-------|---------|
| `workModes` | `remote` \| `hybrid` \| `onsite` (multi-select) |
| `locationBuckets` | Corpus buckets to prefer: `nyc` \| `sf` \| `remote` \| `other` |
| `locations` | Free-text places the user cares about (display / soft filter) |
| `onsiteLocations` | Where onsite/hybrid is acceptable. **Required whenever `workModes` includes `hybrid` or `onsite`.** Never treat “open to onsite” as every office worldwide — scope it to these places (and matching `locationBuckets`). |
| `categories` | Preferred role categories (same 15 as corpus) |
| `seniority` | `senior` and/or `mid`; extra signals `staff+` / `intern` are honored when present |
| `track` | `ic` \| `manager` \| `either` (individual contributor vs people manager) |
| `companyStages` | Free-form tags the user cares about (e.g. `seed`, `series-a`, `growth`, `public`) |
| `companySizes` | Optional size bands the user stated (free-form) |
| `industries` | Domains from résumé + interview (free-form) |
| `formerEmployers` | Company names from the résumé (past employers); used with `formerEmployerPolicy` |
| `formerEmployerPolicy` | `include` — allow roles there · `exclude` — skip them in discover/search defaults · `ask` — confirm per company when they appear |
| `salaryMin` | Annual USD floor, or `null` if undisclosed / no floor |
| `mustHaves` | Short soft requirements |
| `dealBreakers` | Short exclusions |
| `notes` | Catch-all soft constraints |
| `interviewComplete` | `true` after the user finishes the preferences interview |

Extra keys are allowed when the interview surfaces something useful (visa, travel %, commute, “staff+ only”, etc.) — keep values JSON-serializable.

`network-jobs` should apply these as **defaults** when the user does not override in the query. User query always wins.

## resume/

| Path | Purpose |
|------|---------|
| `resume/source.*` | Original file from `network-jobs profile import` |
| `resume/text.md` | Extracted text for profile fill, prefs interview, and intro drafts |

PII — never commit `~/.network-jobs/resume/` into git.

## connections.json

Array of people from LinkedIn `Connections.csv`:

```json
[
  {
    "firstName": "Ada",
    "lastName": "Lovelace",
    "company": "Analytical Engines Inc",
    "position": "Engineer",
    "url": "https://www.linkedin.com/in/ada",
    "email": "",
    "connectedOn": "01 Jan 2024"
  }
]
```

## companies.json

Aggregated company graph (connection counts + sample people):

```json
[
  {
    "name": "Stripe",
    "normalized": "stripe",
    "slug": "stripe",
    "domain": "",
    "connectionCount": 12,
    "people": [
      { "name": "Jane Doe", "position": "PM", "url": "https://www.linkedin.com/in/jane" }
    ],
    "lastCrawl": "2026-09-16T02:00:00Z",
    "listingSetHash": "a1b2c3d4e5f60789",
    "jobsUrl": "https://api.example.com/v1/jobs",
    "lastPagination": { "pages": 4, "complete": true, "truncated": false }
  }
]
```

- `normalized` — lowercase, punctuation/suffix stripped (see import helper).
- `slug` — filesystem-safe form of `normalized`.
- `jobsUrl` — listings JSON endpoint stamped by `crawl-state --stamp --source-url`;
  `network-jobs refresh` re-crawls it deterministically (no model in the loop).
- `domain` — filled later during careers discovery when known.
- `people` — up to 10 sample connections (not the full roster). **Intro ranking joins `connections.json`**, not this sample.
- `lastCrawl` / `listingSetHash` / `lastPagination` — crawl budget. If the listing-set hash matches, skip refresh/ingest (delta is empty). Stamp after a successful paginated extract. Caps: 15 API pages, 5 browser “load more” pages, 2000 listings.

## Triage (careers-discover output)

Staging only. Do **not** write corpus shards from `careers-discover`.

### index/listings.json

Raw extracted openings (pre-normalization):

```json
[
  {
    "title": "Senior Backend Engineer",
    "location": "San Francisco, CA",
    "locations": ["San Francisco, CA"],
    "url": "https://example.com/jobs/123",
    "department": "Infrastructure",
    "externalId": "123",
    "salary": { "min": 180000, "max": 250000 },
    "postedAt": "2025-12-15T00:00:00Z",
    "sourceUrl": "https://example.com/careers",
    "rawNotes": ""
  }
]
```

`locations` is optional (one posting, many offices). `externalId` is the ATS/board id when the JSON exposes one — used for fingerprinting, never invented.

### index/pagination.json

Written by `careers-discover/helpers/paginate-listings.py` when a jobs JSON/API is followed (page / cursor / offset). Cap `maxPages` (default 15). ATS-agnostic — no adapter matrix.

```json
{
  "pages": 4,
  "complete": true,
  "truncated": false,
  "scheme": "link",
  "maxPages": 15
}
```

Also copied into the INVENTORY `Pagination:` line. **`complete` is false** when the cap truncated the crawl or a next-page signal remained. Ingest must **not** expire unseen jobs unless `complete` is true.

### index/matches.json

Written by `careers-discover/helpers/match-prefs.py` after extract. Score listings against `preferences.json` (+ résumé keywords when present). **Confirm matches by default** at ingest time; the user can still say “ingest all” (`listings.json`) or a department slice.

```json
{
  "nListings": 120,
  "nMatches": 14,
  "showing": "14 of 120 match prefs",
  "departments": { "Product": 40, "Engineering": 80 },
  "ingestDefault": "matches",
  "jobs": [
    {
      "title": "Staff Product Manager, Growth",
      "location": "New York, NY or Remote",
      "url": "https://example.com/jobs/pm-2",
      "department": "Product",
      "matchScore": 15,
      "matchReasons": ["remote", "onsiteLocations", "category", "seniority", "track"],
      "matched": true
    }
  ]
}
```

### INVENTORY.md

Required. Summarize: company, careers URL used, listing count, caveats, suggested next steps.

Helpers append a `<!-- nj-summary -->` block with **N of M match prefs**, a department histogram, and (later) pagination. Do not dump the full board into chat — point at `matches.json`.

### fetch-log/

Verbatim capture of each fetch/browser snapshot **before** presenting results to the user. One JSON file per call:

```json
{
  "timestamp": "2026-07-08T19:00:00Z",
  "method": "curl|agent-browser|user-capture",
  "url": "https://example.com/careers",
  "status": 200,
  "disposition": "staged",
  "notes": ""
}
```

## Corpus (jobs-ingest output)

### Job object

```json
{
  "id": "stripe-senior-backend-engineer-123",
  "fingerprint": "id:stripe:123",
  "title": "Senior Backend Engineer",
  "company": "Stripe",
  "companyDomain": "stripe.com",
  "department": "Developer Infrastructure",
  "category": "engineering",
  "location": "San Francisco, CA",
  "locations": [{"raw": "San Francisco, CA", "city": "San Francisco", "region": "CA", "remote": false, "bucket": "sf"}],
  "locationBucket": "sf",
  "locationBuckets": ["sf"],
  "seniority": "senior",
  "track": "ic",
  "url": "https://stripe.com/jobs/123",
  "externalId": "123",
  "status": "open",
  "salary": { "min": 180000, "max": 250000 },
  "postedAt": "2025-12-15T00:00:00Z",
  "firstSeen": "2026-07-08",
  "lastSeen": "2026-07-08"
}
```

Identity is **`fingerprint`**, not URL: `id:{company}:{atsId}` when `externalId` is known, otherwise `fp:{company}:{sha1(title+locations)}`. Rebuild merges on fingerprint (incoming wins, `firstSeen` preserved). `status` is `open` | `closed`. Closed jobs stay in `jobs-all.json` but are omitted from searchable shards.

**Expiry / close:** when ingesting a company, unseen open jobs for that company are marked `closed` **only if** triage `pagination.complete` is true. Incomplete crawls (truncated, cap hit, missing next page) must not expire anything.

### Categories (15)

`engineering` | `product` | `design` | `data` | `ai-ml` | `sales` | `marketing` | `customer-success` | `operations` | `finance` | `people` | `legal` | `it-security` | `retail` | `other`

### Location buckets

| Bucket | Meaning |
|--------|---------|
| `nyc` | New York City metro |
| `sf` | San Francisco / Bay Area |
| `remote` | Fully remote (or remote-first) |
| `other` | Everything else |

Hybrid strings such as `New York, NY or Remote` set **`locationBuckets`: `["nyc","remote"]`** so the same job is written to both granular shards. Parsed `locations[].city` / `.region` are used with `onsiteLocations` (never “every office worldwide”).

### Seniority buckets

Keep `senior` / `mid` shards as the fast path.

| Bucket | Title signals |
|--------|----------------|
| `senior` | Senior, Staff, Principal, Lead, Director, VP, Head of, **people-manager titles** (`Engineering Manager`, `Director of Engineering`, …) |
| `mid` | Everything else (including internships) |

Additional **`senioritySignals`** on the job object: `intern`, `staff+`, `manager`. Prefs or queries can filter those without new shard files. Interns stay in `mid`; Staff/Principal stay in `senior` plus `staff+`. People-manager titles (track `manager`) land in `senior` with the `manager` signal — IC-flavored "manager" titles (`Account Manager`, `Program Manager`) stay on the `ic` track and are not promoted.

`track` is persisted on the job (`ic` | `manager`) by the classifier.

### manifest.json

```json
{
  "lastUpdated": "2026-07-08T19:00:00Z",
  "totalJobs": 42,
  "categories": {
    "engineering": {
      "count": 10,
      "file": "engineering.json",
      "byLocation": {
        "nyc": {
          "senior": { "count": 2, "file": "engineering-nyc-senior.json" },
          "mid": { "count": 1, "file": "engineering-nyc-mid.json" }
        }
      }
    }
  }
}
```

## Promotion rules

1. `careers-discover` writes only under `triage/`.
2. `jobs-ingest` promotes triage → corpus **only after user confirmation**.
3. Never delete triage batches without asking.
4. PII (connections, profile) stays local — never commit `~/.network-jobs/` into this repo.

## Skill pipeline

| Skill | Reads | Writes |
|-------|-------|--------|
| `network-jobs-setup` | `resume/`, conversation | `profile.json`, `preferences.json` |
| `network-jobs-import` | LinkedIn ZIP | `connections/`, `companies/` |
| `careers-discover` | `companies/`, `preferences.json` (optional focus) | `triage/` (`listings.json` + `matches.json`) |
| `jobs-ingest` | `triage/` (`matches.json` by default, or all / department slice) | `corpus/` |
| `network-jobs` | `corpus/`, `profile.json`, `preferences.json`, `resume/` | `search/ranked.json` |
| `intro-email-generator` | `profile.json`, `resume/text.md`, `connections.json`, `search/intros.json` | `search/intros.json` |

CLI helpers: `network-jobs profile import <file>` stores the résumé; `network-jobs profile show` prints profile + prefs + resume status.

Search ranker: `skills/network-jobs/helpers/rank-jobs.py` writes `search/ranked.json` (`showing: "K of N"`). The search skill reads that file — it does not dump whole shards into context.

### search/ranked.json

```json
{
  "k": 25,
  "n": 430,
  "showing": "25 of 430",
  "query": "senior pm nyc",
  "shards": ["product-nyc-senior.json"],
  "staleHidden": 12,
  "jobs": []
}
```

- `staleHidden` — postings excluded as stale: `postedAt` older than 90 days, or
  no `postedAt` and `lastSeen` older than 120 days. Re-run rank with
  `--include-stale` to see them (they carry `"stale": true` and sort last).
- Recency boost: postings from the last 14 days get +2 (`matchReasons` gains
  `recent`), last 30 days get +1.

