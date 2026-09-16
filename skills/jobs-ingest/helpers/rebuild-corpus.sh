#!/usr/bin/env bash
# Rebuild corpus shards + manifest from a flat jobs JSON array.
# Merges with existing corpus/jobs-all.json by fingerprint (not URL).
# Expire/close unseen jobs for a company ONLY with --pagination-complete.
set -euo pipefail

ALL_JSON="${1:-}"
if [[ -z "$ALL_JSON" || ! -f "$ALL_JSON" ]]; then
  echo "Usage: rebuild-corpus.sh <jobs-batch.json> [--expire-company SLUG] [--pagination-complete]" >&2
  echo "  Merges into existing corpus by fingerprint; input jobs win on conflict." >&2
  echo "  Unseen jobs are closed only when --pagination-complete is set." >&2
  exit 1
fi
shift || true

EXPIRE_COMPANY=""
COMPLETE=0
while [[ $# -gt 0 ]]; do
  case "$1" in
    --expire-company) EXPIRE_COMPANY="$2"; shift 2 ;;
    --pagination-complete) COMPLETE=1; shift ;;
    --pagination-incomplete) COMPLETE=0; shift ;;
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

python3 -m network_jobs.cli "${args[@]}"
