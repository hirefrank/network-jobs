# AGENTS.md

Coding-agent guide for `worker/` (hosted sunset only).

## Scope

Cloudflare Worker **`jobs-api`** serves `jobs.hirefrank.com` with HTTP 410 JSON and an HTML sunset page. Local product code lives in the repo root (`skills/`, `bin/`, etc.) — not here.

## Commands

From `worker/`:

```bash
bun install
bun run test
bun run typecheck
bun run deploy
```

## Documentation

- [`SUNSET.md`](./SUNSET.md) — history and verification curls
- [`../docs/DECOMMISSION.md`](../docs/DECOMMISSION.md) — checklist
- [`../docs/hosted-d1-export.md`](../docs/hosted-d1-export.md) — archived D1 backup notes

## Done checklist

1. `bun run test` passes before deploy.
2. After deploy, verify 410 on `/hirefrank/advisor.json` and HTML on `/` with `Accept: text/html`.
