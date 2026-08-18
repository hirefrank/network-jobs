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

```json
{
  "profile (see profile.json)": "hirefrank",        // Advisor's unique identifier
  "lastUpdated": "2026-01-09T22:30:00Z",  // When data was last refreshed
  "totalJobs": 430,                  // Total jobs across all categories
  "categories": {
    "engineering": {
      "count": 70,                   // Jobs in this category
      "file": "engineering.json",    // Filename to fetch
      "lastUpdated": "2026-01-09T22:30:00Z"
    }
    // ... more categories
  }
}
```

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
| `manifest.lastUpdated` | When network data was last refreshed |

**Freshness logic:**
- Jobs refreshed every 6 hours
- Display age using `postedAt` (preferred) or `firstSeen` (fallback)
- If `lastSeen` is older than 24 hours, job may have been filled
- New jobs: `postedAt` or `firstSeen` within last 7 days

## Troubleshooting

### Manifest Not Loading

```
Error: Failed to fetch manifest
```

**Causes:**
1. Wrong advisor slug
2. Network connectivity issue
3. CORS restriction (if running in browser)

**Solution:** Verify advisor slug, try the fetch command directly.

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

## API Endpoints

**Base URL:** `local corpus under ~/.network-jobs/corpus`

| Endpoint | Purpose |
|----------|---------|
| `/{profile (see profile.json)}/advisor.json` | Get advisor info (name, email, title) |
| `/{profile (see profile.json)}/manifest.json` | Get categories and job counts |
| `/{profile (see profile.json)}/{category}.json` | Get all jobs in a category |
| `/{profile (see profile.json)}/{category}-{location}-{seniority}.json` | Get granular subset |

**Examples:**
```bash
# Get advisor info
curl -s "local corpus under ~/.network-jobs/corpus/hirefrank/advisor.json"

# Get manifest
curl -s "local corpus under ~/.network-jobs/corpus/hirefrank/manifest.json"

# Get engineering jobs
curl -s "local corpus under ~/.network-jobs/corpus/hirefrank/engineering.json"

# Get senior PM jobs in NYC
curl -s "local corpus under ~/.network-jobs/corpus/hirefrank/product-nyc-senior.json"
```

## Rate Limits

No rate limits currently enforced. However:
- Cache manifest for duration of conversation
- Fetch only needed category files
- Don't fetch all 15 categories unless necessary
