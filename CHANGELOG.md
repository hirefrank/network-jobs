# Changelog

## v1.5.0 — 2026-09-29

Location correctness, review precision, ingest safety, and fit evidence
(issues #11–#16).

### Locations
- Unknown-location sentinels (`N/A`, …) never match onsite prefs; short
  tokens match only on word boundaries (`DC` still hits `Washington, DC`;
  `N` can no longer ride inside `New York`).
- `parse_locations` is idempotent and splits comma-separated multi-city
  strings (`San Francisco, Seattle, …` → one entry per city); `City, ST`
  pairs stay whole. `anywhere`/`global`/`worldwide` parse as remote.

### Review & intros
- `review-matches` clusters by `head/domain` family stems
  (`product/payments`), each with a suggested `--veto` phrase.
- `intros --title/--url/--company` targets reviewed roles; empty selection
  is an error, not a silent default.
- `search -v` appends a fit brief per role (reasons, résumé hits, warmth,
  gaps); default output unchanged.

### Safety
- Expiry refuses filtered batches: `--expect-count` (board size) makes
  matches-only ingest skip closing live roles, loudly; `--force-expire`
  overrides. The skill always passes the board size now.

## v1.4.0 — 2026-09-29

New commands plus extraction and precision fixes (issues #6–#10).

### Extraction
- Greenhouse `boards-api` object-`location` payloads now normalize instead of
  passing through verbatim (type-aware staged guard in `normalize_listing`).
- Prose placeholder ATS ids (`See Opening ID`, … — 20 entries) filter to
  absent, so boards stop collapsing onto one shared fingerprint.

### Matching & review
- `match-prefs` prints composition (`matchDepartments`, `matchCategories`,
  `reasonCounts`) and warns on unconfirmed empty `dealBreakers` (new
  `dealBreakersConfirmed` flag, set by the interview).
- New `review-matches`: family clustering, leak reports, `--veto` loop that
  rewrites prefs and rematches in one step.
- Interview confirms proposed categories (with affinity warning) and always
  asks deal-breakers explicitly.
- Hard-fail reasons now recorded (`category/location/track-mismatch`).

### Reporting & packs
- New `report`: sanitized diagnostic bundle (PII redacted) → GitHub issue,
  plus an agent nudge to offer filing.
- `build-pack` / `fetch-pack` wired into the `network-jobs` CLI.

## v1.3.2 — 2026-09-29

- **Muse support in setup** — `network-jobs setup --agent auto` detects the
  `muse` CLI and links all six skills into the shared `~/.agents/skills`
  (verified: Muse reads that dir). `network-jobs agents` lists it, and
  detection also works off the binary when no home dir exists.
- **LICENSE capitalization fix** (hirefrank, lowercase one word).
- Landing page shipped at `hirefrank.com/network-jobs` (site only, not in
  the npm tarball).

## v1.3.1 — 2026-09-29

First npm release (`@hirefrank/network-jobs`). Install with
`npm i -g @hirefrank/network-jobs@latest && network-jobs setup --agent auto`
(`npx --yes @hirefrank/network-jobs@latest setup …` for zero-install).

- **`network-jobs update` handles npm-global installs** — detects
  `*/lib/node_modules/@hirefrank/network-jobs` and refreshes via
  `npm i -g @hirefrank/network-jobs@latest` instead of purging the npx cache.
- **Launcher + setup hints prefer the registry** over the GitHub tarball.
- **Packaging fixes** — `publishConfig.access: public`, normalized `bin` path,
  merged duplicate `scripts` keys, `prepack` removes `__pycache__/` so test
  runs never pollute the tarball.

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
