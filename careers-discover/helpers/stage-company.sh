#!/usr/bin/env bash
# Create a triage skeleton for one company careers scrape.
set -euo pipefail

NAME="${1:-}"
SLUG="${2:-}"
if [[ -z "$NAME" ]]; then
  echo "Usage: stage-company.sh <Company Name> [slug]" >&2
  exit 1
fi

DATA="${NETWORK_JOBS_HOME:-$HOME/.network-jobs}"
DATE="$(date -u +%Y-%m-%d)"
if [[ -z "$SLUG" ]]; then
  SLUG="$(echo "$NAME" | tr '[:upper:]' '[:lower:]' | sed -E 's/[^a-z0-9]+/-/g; s/^-|-$//g')"
fi

DIR="$DATA/triage/careers-${SLUG}-${DATE}"
mkdir -p "$DIR/index" "$DIR/fetch-log"

if [[ ! -f "$DIR/index/listings.json" ]]; then
  echo '[]' > "$DIR/index/listings.json"
fi

if [[ ! -f "$DIR/INVENTORY.md" ]]; then
  cat > "$DIR/INVENTORY.md" <<EOF
# Careers triage — ${NAME}

- **Slug:** ${SLUG}
- **Date:** ${DATE}
- **Careers URL:** (fill)
- **Listings:** 0
- **Caveats:**
- **Next steps:** Review listings.json, then run jobs-ingest if OK.
EOF
fi

echo "$DIR"
