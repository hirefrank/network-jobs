# Decommission checklist (follow-on)

Do **not** execute until the local suite is dogfooded and replaces your daily Network Jobs workflow.

Tracked as deferred work from the Local Network Jobs Skills plan. The Cloudflare app stays up until parity is good enough.

## When ready

### 1. Biz monorepo (`hirefrank/biz`)

- [ ] Stop vendoring curl-based `network-jobs` from `hirefrank/skills` (or re-point to this suite)
- [ ] Update `.agents/README.md` / operator docs to point at this repo’s install
- [ ] Remove Jobs deploy/preview target from `scripts/ci/targets.ts` and `docs/ci.md`
- [ ] Remove root shortcuts (`pnpm deploy:jobs`, `pnpm jobs:health`, etc.) if unused
- [ ] Archive or delete `apps/jobs` workspace (Worker, D1, R2, Queue, CLI)
- [ ] Remove `packages/cli-core` Jobs HTTP commands if nothing else depends on them
- [ ] Update hirefrank.com/skills marketing away from `jobs.hirefrank.com` JSON

### 2. Cloudflare / hosted

- [ ] Disable crons and queue consumers
- [ ] Export any advisor data you still need into local `~/.network-jobs/`
- [ ] Delete Worker `jobs-api`, D1 `advisor-jobs-db`, R2 `advisor-skills-export`, crawl queue
- [ ] DNS / custom domain for `jobs.hirefrank.com` → sunset or redirect to this README

### 3. Public skills

- [ ] Keep this repo as `hirefrank/network-jobs`
- [ ] Deprecate hosted-dependent skill in `hirefrank/skills` with a README pointer here
- [ ] Announce install:

```bash
npx skills add hirefrank/network-jobs -g -a claude-code -a cursor -a codex
npx github:hirefrank/network-jobs setup --agent auto
```

## Out of scope for decommission PR

- Porting ATS adapters (intentionally abandoned)
- Migrating multi-advisor SaaS tenants (local-first only)
