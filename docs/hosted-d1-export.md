# Hosted D1 export (archived)

**2026-10-04:** Full remote export `advisor-jobs-db-2026-10-04.sql` (~1.5 GB) was taken before D1 `advisor-jobs-db` was deleted.

- Operator copy: upload to Google Drive (not in git).
- Historical path during biz monorepo sunset: `hirefrank/biz` `apps/jobs/exports/` (gitignored SQL).

There is no automatic importer into `~/.network-jobs/`. Advisors reinstall via `network-jobs setup` + LinkedIn import.

Regenerate is **not possible** after D1 deletion unless a new database is created.
