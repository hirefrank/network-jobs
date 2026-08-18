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
│       │   └── listings.json
│       └── fetch-log/
│           └── <timestamp>-<label>.json
├── corpus/
│   ├── manifest.json
│   ├── <category>.json
│   └── <category>-<loc>-<seniority>.json
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
| `seniority` | `senior` and/or `mid` |
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
    ]
  }
]
```

- `normalized` — lowercase, punctuation/suffix stripped (see import helper).
- `slug` — filesystem-safe form of `normalized`.
- `domain` — filled later during careers discovery when known.
- `people` — up to 10 sample connections (not the full roster).

## Triage (careers-discover output)

Staging only. Do **not** write corpus shards from `careers-discover`.

### index/listings.json

Raw extracted openings (pre-normalization):

```json
[
  {
    "title": "Senior Backend Engineer",
    "location": "San Francisco, CA",
    "url": "https://example.com/jobs/123",
    "department": "Infrastructure",
    "salary": { "min": 180000, "max": 250000 },
    "postedAt": "2025-12-15T00:00:00Z",
    "sourceUrl": "https://example.com/careers",
    "rawNotes": ""
  }
]
```

Omit fields you did not observe. Never invent salary or posted dates.

### INVENTORY.md

Required. Summarize: company, careers URL used, listing count, caveats, suggested next steps.

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
  "title": "Senior Backend Engineer",
  "company": "Stripe",
  "companyDomain": "stripe.com",
  "department": "Developer Infrastructure",
  "category": "engineering",
  "location": "San Francisco, CA",
  "locationBucket": "sf",
  "seniority": "senior",
  "url": "https://stripe.com/jobs/123",
  "salary": { "min": 180000, "max": 250000 },
  "postedAt": "2025-12-15T00:00:00Z",
  "firstSeen": "2026-07-08",
  "lastSeen": "2026-07-08"
}
```

### Categories (15)

`engineering` | `product` | `design` | `data` | `ai-ml` | `sales` | `marketing` | `customer-success` | `operations` | `finance` | `people` | `legal` | `it-security` | `retail` | `other`

### Location buckets

| Bucket | Meaning |
|--------|---------|
| `nyc` | New York City metro |
| `sf` | San Francisco / Bay Area |
| `remote` | Fully remote (or remote-first) |
| `other` | Everything else |

### Seniority buckets

| Bucket | Title signals |
|--------|----------------|
| `senior` | Senior, Staff, Principal, Lead, Director, VP, Head of |
| `mid` | Everything else |

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
| `careers-discover` | `companies/`, `preferences.json` (optional focus) | `triage/` |
| `jobs-ingest` | `triage/` | `corpus/` |
| `network-jobs` | `corpus/`, `profile.json`, `preferences.json` | — |
| `intro-email-generator` | `profile.json`, `resume/text.md`, job context | — (draft in chat) |

CLI helpers: `network-jobs profile import <file>` stores the résumé; `network-jobs profile show` prints profile + prefs + resume status.
