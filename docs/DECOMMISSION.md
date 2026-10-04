# Decommission checklist (follow-on)

**Status (2026-10-04):** Preconditions met — the local suite is dogfooded and
shipped (v1.6.0, all issues through #23 closed). Single-phase sunset decided,
no notice period (~3 active users). The full sunset plan (including the
sunset-worker reference implementation) lives in `apps/jobs/SUNSET.md` in
`hirefrank/biz` — see GitHub permalink:
https://github.com/hirefrank/biz/blob/main/apps/jobs/SUNSET.md

## Pre-sunset validation (run before deploying sunset worker)

- [ ] **3-user smoke test**: For each active advisor, verify their automation
  handles the migration response:
  ```bash
  # Simulate what clients will see post-sunset
  curl -i https://jobs.hirefrank.com/api/v1/jobs
  # Expect: 410 Gone + JSON body with migrateTo/install fields
  ```
  Confirm their scripts/agents either (a) surface the migration message to the
  user, or (b) auto-install the local suite via the `install` hint.

- [x] **D1 full export** (2026-10-04): `hirefrank/biz` → `apps/jobs/exports/advisor-jobs-db-2026-10-04.sql` (~1.5 GB, gitignored). Upload to Google Drive before deleting D1. There is no automatic importer into `~/.network-jobs/` — advisors reinstall via `network-jobs setup` + LinkedIn ZIP import.

- [ ] **Secrets audit**: List all `jobs-api` secrets and bindings:
  ```bash
  wrangler secret list --env production
  wrangler whoami  # confirm account
  ```
  After D1/R2 deletion, redeploy sunset worker *without* those bindings.

## When ready

### 1. Biz monorepo (`hirefrank/biz`)

- [ ] Stop vendoring curl-based `network-jobs` from `hirefrank/skills`; re-point to this suite (`github:hirefrank/network-jobs#main`)
- [ ] Update `.agents/README.md` / operator docs to point at this repo’s install
- [ ] Remove Jobs deploy/preview target from `scripts/ci/targets.ts` and `docs/ci.md`
- [ ] Remove root shortcuts (`pnpm dev:jobs`, `build:jobs`, `deploy:jobs`, `jobs:cli`, `jobs:health`, `jobs:crawl:*`, `hf:jobs`) if unused
- [ ] Archive or delete `apps/jobs` workspace (Worker `jobs-api`, D1 `advisor-jobs-db`, R2 `advisor-skills-export`, crawl queue, 2 crons) — after the sunset worker is deployed (see `apps/jobs/SUNSET.md` in `hirefrank/biz`)
- [ ] Remove `packages/cli-core` Jobs HTTP commands (`commands/jobs.ts`, `commander/jobs.ts`, `jobs-admin.ts`, exports, `HF_BINARY_OWNED_NAMESPACES`) if nothing else depends on them
- [ ] Update the `network-jobs` entry in the `hirefrank/skills` repo:
    - Skill source: `github:hirefrank/network-jobs#main` (or pin to `v1.6.0` for reproducibility)
    - Landing page: `https://hirefrank.com/network-jobs/`
    - This feeds both `hirefrank.com/skills` via `www/src/lib/github-skills.ts` and biz vendoring via `skills-lock.json` — bump the lockfile after merging the skills repo change

### 2. Cloudflare / hosted — single-phase sunset

- [ ] Deploy the sunset worker as `jobs-api` (reference implementation in `apps/jobs/SUNSET.md` in `hirefrank/biz`): `410 Gone` + migration JSON for API/agent clients, human sunset page for browsers. Keep worker name and routes.
- [ ] Verify: API routes → 410, browsers → sunset page
- [ ] Disable crons and queue consumers (remove the triggers)
- [ ] Delete D1 `advisor-jobs-db`, R2 `advisor-skills-export`, crawl queue; keep the sunset worker as the permanent address for `jobs.hirefrank.com` (advisor data already exported in pre-sunset validation)
- [ ] **Secrets cleanup**: Remove `jobs-api` bindings/secrets for deleted D1/R2; redeploy sunset worker with only KV/assets bindings it actually needs
- [ ] `jobs.hirefrank.com` → sunset page (stays); no redirect needed

### 3. Public skills

- [ ] Keep this repo as `hirefrank/network-jobs`
- [ ] Deprecate the hosted-API-dependent skill in `hirefrank/skills` (the one that wraps `jobs.hirefrank.com`); add a README pointer to this suite. The new skill-suite entry (above) stays active.
- [ ] Announce install:

```bash
npx skills add hirefrank/network-jobs -g -a claude-code -a cursor -a codex
npm i -g @hirefrank/network-jobs@latest && network-jobs setup --agent auto
```

## Out of scope for decommission PR

- Porting ATS adapters (intentionally abandoned)
- Migrating multi-advisor SaaS tenants (local-first only)
