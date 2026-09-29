#!/usr/bin/env bash
# Rebuild corpus shards + manifest from a flat jobs JSON array.
# Merges with existing corpus/jobs-all.json by fingerprint (not URL).
# Expire/close unseen jobs for a company ONLY with --pagination-complete,
# and never on a filtered (subset) batch unless --force-expire.
set -euo pipefail

ALL_JSON="${1:-}"
if [[ -z "$ALL_JSON" || ! -f "$ALL_JSON" ]]; then
  echo "Usage: rebuild-corpus.sh <jobs-batch.json> [--expire-company SLUG] [--pagination-complete] [--expect-count N] [--force-expire]" >&2
  echo "  Merges into existing corpus by fingerprint; input jobs win on conflict." >&2
  echo "  Unseen jobs are closed only when --pagination-complete is set." >&2
  echo "  With --expect-count, expiry is skipped when the batch is a strict" >&2
  echo "  subset (matches-only ingest); pass --force-expire to override." >&2
  exit 1
fi
shift || true

EXPIRE_COMPANY=""
COMPLETE=0
EXPECT_COUNT=""
FORCE_EXPIRE=0
while [[ $# -gt 0 ]]; do
  case "$1" in
    --expire-company) EXPIRE_COMPANY="$2"; shift 2 ;;
    --pagination-complete) COMPLETE=1; shift ;;
    --pagination-incomplete) COMPLETE=0; shift ;;
    --expect-count) EXPECT_COUNT="$2"; shift 2 ;;
    --force-expire) FORCE_EXPIRE=1; shift ;;
    *)
      echo "Unknown arg: $1" >&2
      exit 1
      ;;
  esac
done

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
export PYTHONPATH="${ROOT}/lib${PYTHONPATH:+:$PYTHONPATH}"
export NETWORK_JOBS_SUITE="${NETWORK_JOBS_SUITE:-$ROOT}"

args=(-v rebuild "$ALL_JSON")
if [[ -n "$EXPIRE_COMPANY" ]]; then
  args+=(--expire-company "$EXPIRE_COMPANY")
fi
if [[ "$COMPLETE" -eq 1 ]]; then
  args+=(--pagination-complete)
else
  args+=(--pagination-incomplete)
fi
if [[ -n "$EXPECT_COUNT" ]]; then
  args+=(--expect-count "$EXPECT_COUNT")
fi
if [[ "$FORCE_EXPIRE" -eq 1 ]]; then
  args+=(--force-expire)
fi

python3 -m network_jobs.cli "${args[@]}"
