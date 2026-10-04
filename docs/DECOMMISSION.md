# Decommission checklist (hosted Network Jobs)

**Status (2026-10-04):** Hosted sunset **complete** in production. Local suite: install via `network-jobs setup`. Sunset worker source: [`worker/`](./../worker/) — ops sequence in [`worker/SUNSET.md`](../worker/SUNSET.md).

## Pre-sunset validation

- [ ] **Advisor smoke test** (optional at ~3 users): confirm automations surface the migration JSON when they hit the old host:
  ```bash
  curl -sS -D - -o /tmp/jobs-retire.json \
    -H 'Accept: application/json' \
    'https://jobs.hirefrank.com/hirefrank/advisor.json'
  # Expect: HTTP 410, body fields retired=true, install, docs, github
  jq -r '.retired,.install' /tmp/jobs-retire.json
  ```
- [x] **D1 full export** (2026-10-04): see [`docs/hosted-d1-export.md`](./hosted-d1-export.md). Upload operator copy to Google Drive.
- [ ] **Secrets audit** (operator): from `worker/`, `bun run wrangler secret list`; remove crawl/API secrets no longer needed; redeploy if dashboard shows stale bindings.

## Biz monorepo (`hirefrank/biz`)

- [x] Remove Jobs deploy/preview target from `scripts/ci/targets.ts` and `docs/ci.md` (2026-10-04, PR #140).
- [x] Remove unused biz shortcuts (`dev:jobs`, `build:jobs`, `jobs:*`, `hf:jobs`, `deploy:jobs`); deploy from `worker/` in this repo.
- [x] Remove `hirefrank/biz` `apps/jobs` workspace (pointer README only); sunset worker lives here.
- [x] Omit `hf jobs` from built registry (`scripts/generate-cli-registry.ts` `SKIP_FILES` includes `jobs.ts`).
- [x] Vendored `.agents/skills/network-jobs` points at local corpus paths (not live `curl` to `jobs.hirefrank.com`).
- [ ] Repoint `skills-lock.json` / **`hirefrank/skills`** `network-jobs` entry to `github:hirefrank/network-jobs#main` (public skills site + lockfile bump).
- [ ] Remove or archive `packages/cli-core` Jobs HTTP modules (`commands/jobs.ts`, `commander/jobs.ts`, `jobs-admin.ts`) if sandbox no longer needs them.

## Cloudflare / hosted

- [x] Deploy sunset worker as `jobs-api` on `jobs.hirefrank.com` (Worker custom domain; R2 custom domain removed).
- [x] Verify: JSON skill paths → `410` + `retired`; browsers → HTML sunset page.
- [x] Disable crons and delete jobs crawl queue (`crawl-queue`); do **not** delete Rouxlette `crawler-queue` / `crawler-dlq`.
- [x] Delete D1 `advisor-jobs-db`.
- [ ] Confirm R2 `advisor-skills-export` (and any jobs export buckets) deleted after emptying (operator).
- [ ] Secrets/bindings cleanup on `jobs-api` after operator audit.

## Public skills

- [x] Canonical product repo: **`hirefrank/network-jobs`** (this repo).
- [ ] Deprecate hosted-API skill copy in **`hirefrank/skills`**; README pointer to this suite + install below.
- [ ] Announce / document install (www, skills index):

```bash
npx skills add hirefrank/network-jobs -g -a claude-code -a cursor -a codex
npm i -g @hirefrank/network-jobs@latest && network-jobs setup --agent auto
```

## Out of scope

- Porting ATS adapters (intentionally abandoned).
- Migrating multi-advisor SaaS tenants (local-first only).
