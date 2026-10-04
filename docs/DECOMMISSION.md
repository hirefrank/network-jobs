# Decommission checklist (hosted Network Jobs)

**Status (2026-10-04):** Hosted sunset **complete** in production. Local suite remains **`hirefrank/network-jobs`** (install via `network-jobs setup`). Sunset worker source and ops sequence: [`apps/jobs/SUNSET.md`](https://github.com/hirefrank/biz/blob/main/apps/jobs/SUNSET.md) in `hirefrank/biz`.

## Pre-sunset validation

- [ ] **Advisor smoke test** (optional at ~3 users): confirm automations surface the migration JSON when they hit the old host:
  ```bash
  curl -sS -D - -o /tmp/jobs-retire.json \
    -H 'Accept: application/json' \
    'https://jobs.hirefrank.com/hirefrank/advisor.json'
  # Expect: HTTP 410, body fields retired=true, install, docs, github
  jq -r '.retired,.install' /tmp/jobs-retire.json
  ```
- [x] **D1 full export** (2026-10-04): `hirefrank/biz` → `apps/jobs/exports/advisor-jobs-db-2026-10-04.sql` (~1.5 GB, gitignored). Upload copy to Google Drive (operator). No automatic importer into `~/.network-jobs/` — reinstall via `network-jobs setup` + LinkedIn import.
- [ ] **Secrets audit** (operator): from `hirefrank/biz/apps/jobs`, `bun run wrangler secret list`; remove crawl/API secrets no longer needed; redeploy sunset worker if dashboard still shows stale bindings.

## Biz monorepo (`hirefrank/biz`)

- [x] Remove Jobs deploy/preview target from `scripts/ci/targets.ts` and `docs/ci.md` (2026-10-04, PR #140).
- [x] Remove unused root shortcuts (`dev:jobs`, `build:jobs`, `jobs:*`, `hf:jobs`); keep `pnpm deploy:jobs` for manual sunset deploys.
- [x] Replace hosted `apps/jobs` with sunset worker only; merge to `main` (PR #140).
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
