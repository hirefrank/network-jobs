# Decommission checklist (follow-on)

**Status (2026-10-04):** Preconditions met — the local suite is dogfooded and
shipped (v1.4.0, all 10 issues closed). Single-phase sunset decided, no notice
period (~3 active users). The full sunset plan (including the sunset-worker
reference implementation) lives in `apps/jobs/SUNSET.md` in `hirefrank/biz`.

## When ready

### 1. Biz monorepo (`hirefrank/biz`)

- [ ] Stop vendoring curl-based `network-jobs` from `hirefrank/skills` (or re-point to this suite)
- [ ] Update `.agents/README.md` / operator docs to point at this repo’s install
- [ ] Remove Jobs deploy/preview target from `scripts/ci/targets.ts` and `docs/ci.md`
- [ ] Remove root shortcuts (`pnpm dev:jobs`, `build:jobs`, `deploy:jobs`, `jobs:cli`, `jobs:health`, `jobs:crawl:*`, `hf:jobs`) if unused
- [ ] Archive or delete `apps/jobs` workspace (Worker `jobs-api`, D1 `advisor-jobs-db`, R2 `advisor-skills-export`, crawl queue, 2 crons) — after the sunset worker is deployed (see `apps/jobs/SUNSET.md` in `hirefrank/biz`)
- [ ] Remove `packages/cli-core` Jobs HTTP commands (`commands/jobs.ts`, `commander/jobs.ts`, `jobs-admin.ts`, exports, `HF_BINARY_OWNED_NAMESPACES`) if nothing else depends on them
- [ ] Update the `network-jobs` entry in the `hirefrank/skills` repo to point at this suite + landing page (this feeds both `hirefrank.com/skills` via `www/src/lib/github-skills.ts` and biz vendoring via `skills-lock.json` — neither consumes the hosted JSON directly)

### 2. Cloudflare / hosted — single-phase sunset

- [ ] Deploy the sunset worker as `jobs-api` (reference implementation in `apps/jobs/SUNSET.md` in `hirefrank/biz`): `410 Gone` + migration JSON for API/agent clients, human sunset page for browsers. Keep worker name and routes.
- [ ] Verify: API routes → 410, browsers → sunset page
- [ ] Disable crons and queue consumers (remove the triggers)
- [ ] Export any advisor data you still need into local `~/.network-jobs/`
- [ ] Delete D1 `advisor-jobs-db`, R2 `advisor-skills-export`, crawl queue; keep the sunset worker as the permanent address for `jobs.hirefrank.com`
- [ ] `jobs.hirefrank.com` → sunset page (stays); no redirect needed

### 3. Public skills

- [ ] Keep this repo as `hirefrank/network-jobs`
- [ ] Deprecate hosted-dependent skill in `hirefrank/skills` with a README pointer here
- [ ] Announce install:

```bash
npx skills add hirefrank/network-jobs -g -a claude-code -a cursor -a codex
npm i -g @hirefrank/network-jobs@latest && network-jobs setup --agent auto
```

## Out of scope for decommission PR

- Porting ATS adapters (intentionally abandoned)
- Migrating multi-advisor SaaS tenants (local-first only)
