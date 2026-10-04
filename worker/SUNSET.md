# Sunset plan: hosted Network Jobs (`jobs-api`)

**Status:** Retired — single-phase sunset decided 2026-10-04. **Source lives in this repo** (`worker/`).

## Context

The hosted Network Jobs service was Cloudflare Worker `jobs-api`, D1 `advisor-jobs-db`, R2 `advisor-skills-export`, crawl queue, and cron triggers. It crawled ATS job boards and served advisor-specific job JSON to agentic skills.

It is replaced by **network-jobs** (this repo): free, open-source, local-first.

## The sunset worker

Deploy from `worker/` as `jobs-api` (same worker name). API and agent clients get `410 Gone` + migration JSON; browsers get an HTML sunset page.

**Routing:** `jobs.hirefrank.com` must use a Worker custom domain (`wrangler.toml` `custom_domain = true`), not an R2 custom domain.

Implementation: [`src/index.ts`](./src/index.ts).

## Ops sequence

1. From `worker/`: `bun install && bun run deploy`
2. Verify:
   - `curl -s -o /dev/null -w "%{http_code}\n" https://jobs.hirefrank.com/hirefrank/advisor.json` → `410`
   - `curl -s https://jobs.hirefrank.com/hirefrank/advisor.json | jq -r .retired` → `true`
   - `curl -sH "Accept: text/html" https://jobs.hirefrank.com/ | head -c 120` → sunset page
3. **D1 backup:** see [`docs/hosted-d1-export.md`](../docs/hosted-d1-export.md) (export taken 2026-10-04; D1 deleted).
4. Cloudflare teardown (operator): crons, `crawl-queue`, D1, R2 export buckets — keep this worker on `jobs.hirefrank.com`.

## What stays

- `jobs.hirefrank.com` → this worker.
- Product install: https://hirefrank.com/network-jobs/ · https://github.com/hirefrank/network-jobs
