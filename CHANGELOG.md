# Changelog

## v1.3.0 — 2026-09-28

Everything since v1.2.0: five rounds of matching/ranking review, a full
first-time-user dogfood pass, and the fixes it found.

### Matching & ranking
- **Round 2** — seniority fix, recency/stale ranking, keyword cleanup, search/companies refresh
- **Round 3** — ranking quality, ingest hygiene, demo CLI
- **Round 4** — seniority is a soft signal, not a veto
- **Round 5** — opt-in semantic (embedding) matching: fastembed by default with
  Ollama fallback (never raises, never downloads on detection), incremental
  `corpus/embeddings.json` cache at rebuild, `resume-semantic` (+0–4, replaces
  the keyword bonus) and `query-semantic` (+0–2, additive) signals,
  `network-jobs embed-setup` one-time setup and embedding coverage in
  `network-jobs doctor`

### CLI
- **New `network-jobs intros`** — pick 1–2 roles from the last search plus 1–2
  forwarders each from your connections (writes `search/intros.json` for the
  intro-email-generator skill). Previously reachable only via the skill helper,
  which `search` advertised as a follow-on step with no command to run.
- **`embed-setup` reports the real failure** when a provider is detected but the
  warmup embed fails (e.g. model download blocked) — previously it misleadingly
  printed "fastembed is not installed" and re-ran pip install. Exit 1 with the
  underlying reason; the Ollama → fastembed fallback is unchanged.
- **`doctor` shows the embedding section** — provider + cache coverage were added
  to the Python doctor in round 5 but the bash CLI's native doctor never
  surfaced them.
- **CLI resolves npm `.bin` symlinks** when locating the suite — the README
  `npx` one-liner (and `network-jobs update`) failed without this.

### First-run reliability (from a clean-install dogfood as a new user)
- `setup --no-browser` is persisted so `doctor` stops nagging on re-runs
- `parse-linkedin.sh` prints one summary line; full JSON stays in the log
- All `DATA=` assignments across the skills carry "always resolve from the env"
- `embed-setup` pip failure names the real PEP 668 options
- README Fixtures block uses the installed CLI + `network-jobs which`
- `tests/` now ships in the npm package so the fixtures test command works

### Docs
- README "For agents" section near the top (install → setup skill → skill table)
- Agent Skills compatibility list (Claude Code, Cursor, Codex, OpenCode, Pi,
  Grok Bot, Muse, and others)

### CI
- `tests/run.sh` runs on Python 3.11, 3.12, and 3.13
