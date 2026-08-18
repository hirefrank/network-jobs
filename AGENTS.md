## Learned User Preferences

- Prefer a public, installable multi-agent skill suite (gstack/Keep-style CLI) over Claude-only or private-only packaging.
- Prefer ATS-agnostic, model-driven career-page discovery and parsing rather than hard-coded ATS adapters.
- Day-to-day use should be in the agent after one-time CLI setup; keep the CLI for setup, doctor, and optional import.
- Do not commit real LinkedIn connection dumps or other personal network PII; keep only synthetic fixtures in-repo.

## Learned Workspace Facts

- Public repo is `hirefrank/network-jobs`; this workspace is the local skill suite at `~/Projects/network-jobs`.
- Runtime data lives under `~/.network-jobs/` and is shared across agents (Claude Code, Cursor, Codex, etc.).
- Skills live under `skills/`; install via `npx skills add hirefrank/network-jobs` and/or `network-jobs setup --agent`.
- Clone or install the suite as `network-jobs-suite` (not `network-jobs`) so the `network-jobs` skill can be symlinked without path collision.
- Pipeline is import → careers-discover (stage only) → user confirm → jobs-ingest → search → warm intro; never invent job fields; the suite has no hosted API (local files only).
- Scraping-skill patterns are modeled after `~/Projects/provenance`; Cloudflare `apps/jobs` decommission notes live in `docs/DECOMMISSION.md`.
