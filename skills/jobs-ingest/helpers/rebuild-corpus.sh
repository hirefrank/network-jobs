#!/usr/bin/env bash
# Rebuild corpus shards + manifest from a flat jobs JSON array.
# Merges with existing corpus/jobs-all.json by fingerprint (not URL).
# Expire/close unseen jobs for a company ONLY with --pagination-complete,
# and never on a filtered (subset) batch unless --force-expire.
# --delta marks a new/updated-only batch: expiry is always skipped, even
# with --force-expire (re-ingest the full board to expire).
# --filtered marks a filtered crawl: expiry is skipped unless --force-expire
# asserts the filter covers the company.
# --pagination-status blocked|captured always refuses expiry (#39).
# --pagination-status truncated refuses expiry unless --force-expire.
# Zero incoming rows with prior open roles also refuse expiry unless
# --force-expire, whatever the status (omitted, null, or empty).
set -euo pipefail

ALL_JSON="${1:-}"
if [[ -z "$ALL_JSON" || ! -f "$ALL_JSON" ]]; then
  echo "Usage: rebuild-corpus.sh <jobs-batch.json> [--expire-company SLUG] [--pagination-complete] [--pagination-status STATUS] [--expect-count N] [--delta] [--filtered] [--force-expire]" >&2
  echo "  Merges into existing corpus by fingerprint; input jobs win on conflict." >&2
  echo "  Unseen jobs are closed only when --pagination-complete is set." >&2
  echo "  --pagination-status blocked|captured always refuses expiry (unreadable" >&2
  echo "  board / user capture); truncated refuses it unless --force-expire." >&2
  echo "  Zero incoming rows with prior open roles" >&2
  echo "  also refuse expiry unless --force-expire, whatever the status." >&2
  echo "  With --expect-count, expiry is skipped when the batch is a strict" >&2
  echo "  subset for the company (mixed-company rows do not count)." >&2
  echo "  --delta (new/updated-only batch) always skips expiry; to expire," >&2
  echo "  pass the full classified board and omit --delta." >&2
  echo "  --filtered skips expiry unless --force-expire asserts the filter" >&2
  echo "  covers every role for the company." >&2
  exit 1
fi
shift || true

EXPIRE_COMPANY=""
COMPLETE=0
PAGINATION_STATUS=""
EXPECT_COUNT=""
DELTA_ONLY=0
FILTERED=0
FORCE_EXPIRE=0
while [[ $# -gt 0 ]]; do
  case "$1" in
    --expire-company) EXPIRE_COMPANY="$2"; shift 2 ;;
    --pagination-complete) COMPLETE=1; shift ;;
    --pagination-incomplete) COMPLETE=0; shift ;;
    --pagination-status) PAGINATION_STATUS="$2"; shift 2 ;;
    --expect-count) EXPECT_COUNT="$2"; shift 2 ;;
    --delta) DELTA_ONLY=1; shift ;;
    --filtered) FILTERED=1; shift ;;
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
if [[ -n "$PAGINATION_STATUS" ]]; then
  args+=(--pagination-status "$PAGINATION_STATUS")
fi
if [[ "$DELTA_ONLY" -eq 1 ]]; then
  args+=(--delta)
fi
if [[ "$FILTERED" -eq 1 ]]; then
  args+=(--filtered)
fi
if [[ "$FORCE_EXPIRE" -eq 1 ]]; then
  args+=(--force-expire)
fi

python3 -m network_jobs.cli "${args[@]}"
