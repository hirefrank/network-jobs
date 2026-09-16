#!/usr/bin/env bash
# Run helper tests. Quiet unless a test fails.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export PYTHONPATH="$ROOT/lib${PYTHONPATH:+:$PYTHONPATH}"
python3 "$ROOT/tests/test_pipeline.py" "$@"
