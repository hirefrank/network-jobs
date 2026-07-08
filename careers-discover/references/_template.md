# <Source or company pattern>

Brief sentence on what this careers surface is (company site, shared portal family, etc.).

## Cost model

| Action | Cost |
|---|---|
| List openings | free / login / CAPTCHA |
| Job detail | |
| Apply | n/a for this skill |

## Auth

Public? Login wall? Geo block? CAPTCHA?

## Discovery

How to find the careers URL from the company name/domain. Common paths (`/careers`, `/jobs`). Search queries that work.

## Listing index

Where openings appear (DOM region, or JSON URL seen in network tab). Stable job IDs if any. Pagination / infinite scroll traps.

## Detail page

URL pattern for a single job. Fields available (title, location, team, salary, posted date).

## Recipe — quick start

10–20 lines: curl and/or agent-browser from “known domain” → first `listings.json` draft.

## Known caveats

- Edge cases discovered while building this recipe
- Result-set caps, locale mirrors, duplicate postings
