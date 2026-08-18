# Network Jobs - Reference

Detailed reference for category mapping, data interpretation, and troubleshooting.

## Category Mapping

Map user queries to these normalized categories:

| User Says | Category | Examples |
|-----------|----------|----------|
| engineering, developer, software, SWE, backend, frontend, fullstack, devops, SRE, QA, architect | `engineering` | "dev jobs", "software roles", "backend engineer" |
| product, PM, product manager, TPM, program manager | `product` | "PM roles", "product jobs" |
| design, UX, UI, product design, graphic design, brand | `design` | "design jobs", "UX roles" |
| data, analytics, BI, business intelligence, data analyst, data engineer | `data` | "data jobs", "analytics roles" |
| ML, AI, machine learning, artificial intelligence | `ai-ml` | "ML engineer", "AI jobs" |
| sales, AE, account executive, SDR, BDR, business development, solutions engineer | `sales` | "sales jobs", "AE roles" |
| marketing, growth, demand gen, content, PMM, communications, PR | `marketing` | "marketing jobs", "growth roles" |
| customer success, CS, support, CX, account manager (post-sales) | `customer-success` | "CS jobs", "support roles" |
| operations, ops, logistics, supply chain, fulfillment, biz ops | `operations` | "ops jobs", "operations roles" |
| finance, accounting, FP&A, tax, treasury, audit | `finance` | "finance jobs", "accounting roles" |
| HR, recruiting, talent, people ops, L&D | `people` | "HR jobs", "recruiting roles" |
| legal, lawyer, counsel, compliance, policy, contracts | `legal` | "legal jobs", "compliance roles" |
| IT, security, infosec, network admin, sysadmin | `it-security` | "IT jobs", "security roles" |
| retail, store, field sales (in-store) | `retail` | "retail jobs", "store manager" |
| anything else | `other` | "executive assistant", "facilities" |

## Data Schema Details

### manifest.json

Lives at `~/.network-jobs/corpus/manifest.json`.

```json
{
  "lastUpdated": "2026-01-09T22:30:00Z",
  "totalJobs": 430,
  "categories": {
    "engineering": {
      "count": 70,
      "file": "engineering.json",
      "byLocation": {
        "nyc": {
          "senior": { "count": 12, "file": "engineering-nyc-senior.json" },
          "mid": { "count": 9, "file": "engineering-nyc-mid.json" }
        }
      }
    }
  }
}
```

Identity (name, email, title) is separate, in `~/.network-jobs/profile.json`.

### Job Object

```json
{
  "id": 123,                         // Unique job ID
  "title": "Senior Backend Engineer", // Job title (normalized by company)
  "company": "Stripe",               // Company name
  "companyDomain": "stripe.com",     // Company website (useful for identification)
  "department": "Developer Infrastructure",  // Company's internal team name (may be messy)
  "category": "engineering",         // Normalized category
  "location": "San Francisco, CA",   // Location string (format varies)
  "url": "https://stripe.com/jobs/123",  // Direct application link
  "salary": {                        // May be null if not disclosed
    "min": 180000,                   // Minimum salary (annual, USD)
    "max": 250000                    // Maximum salary (annual, USD)
  },
  "postedAt": "2025-12-15T00:00:00Z",   // When job was originally posted (from ATS)
  "firstSeen": "2026-01-01T00:00:00Z",  // When job was first discovered by crawler
  "lastSeen": "2026-01-09T18:00:00Z"    // When job was last confirmed active
}
```

## Location Interpretation

Location strings vary by company. Common patterns:

| Pattern | Meaning |
|---------|---------|
| `Remote` | Fully remote |
| `Remote (US)` | Remote, US-only |
| `Remote - US/Canada` | Remote, US or Canada |
| `San Francisco, CA` | In-office, specific city |
| `New York, NY or Remote` | Hybrid or remote option |
| `Multiple Locations` | Multiple offices, details in job description |

**Filtering tips:**
- Case-insensitive search for "remote"
- City searches: match on city name (e.g., "San Francisco", "NYC", "New York")
- State searches: match on state abbreviation (e.g., "CA", "NY", "TX")

## Salary Interpretation

| Scenario | Interpretation |
|----------|----------------|
| Both `min` and `max` present | Full range disclosed |
| Only `min` present | Minimum salary, no cap disclosed |
| Only `max` present | Up to this amount |
| `salary` is `null` | Not disclosed (common for senior roles) |

**Notes:**
- All salaries are annual, in USD
- Does not include equity, bonuses, or commission
- Some companies don't disclose compensation publicly

## Freshness Indicators

| Field | Use For |
|-------|---------|
| `postedAt` | When job was originally posted (from ATS). Use for freshness display. |
| `firstSeen` | When job was discovered by crawler (fallback if `postedAt` missing) |
| `lastSeen` | Job still active - confirmed within last crawl |
| `manifest.lastUpdated` | When the local corpus was last rebuilt |

**Freshness logic:**
- The corpus only refreshes when the user runs careers-discover + jobs-ingest
- Display age using `postedAt` (preferred) or `firstSeen` (fallback)
- If `manifest.lastUpdated` is more than a week old, suggest re-running discovery
- New jobs: `postedAt` or `firstSeen` within last 7 days

## Troubleshooting

### Manifest Missing or Empty

```
No such file: ~/.network-jobs/corpus/manifest.json
```

**Causes:**
1. `network-jobs setup` was never run
2. Nothing has been ingested yet (`totalJobs: 0`)
3. `NETWORK_JOBS_HOME` points somewhere else

**Solution:** run `network-jobs doctor`, then **careers-discover** followed by **jobs-ingest**.

### Empty Results

```
No jobs found matching your criteria
```

**Causes:**
1. Category doesn't exist in network
2. Filters too restrictive
3. No jobs match all criteria

**Solutions:**
- Check manifest for available categories
- Broaden filters (remove salary requirement, expand location)
- Try related categories

### Category Not Found

```
No category mapping for "nursing"
```

**Cause:** User requested role type not in tech-focused network.

**Solution:** Explain the network's focus, suggest available categories.

## Corpus Files

**Base path:** `${NETWORK_JOBS_HOME:-$HOME/.network-jobs}`

| Path | Purpose |
|------|---------|
| `profile.json` | Your name, email, title (search header + intro footer) |
| `corpus/manifest.json` | Categories, counts, and the granular file map |
| `corpus/{category}.json` | All jobs in a category |
| `corpus/{category}-{location}-{seniority}.json` | Granular shard (preferred read) |
| `corpus/jobs-all.json` | Flat array of every job (rebuild source) |
| `companies/companies.json` | Connection graph by company |

**Examples:**

```bash
DATA="${NETWORK_JOBS_HOME:-$HOME/.network-jobs}"

jq . "$DATA/profile.json"
jq '.categories | keys' "$DATA/corpus/manifest.json"
jq 'length' "$DATA/corpus/engineering.json"
jq '.[] | {title, company, url}' "$DATA/corpus/product-nyc-senior.json"
```

## Read Efficiency

Everything is local, so there are no rate limits — but context is finite:

- Read `manifest.json` once per conversation
- Prefer granular shards over full category files
- Never read `jobs-all.json` for a search; it is the rebuild source
