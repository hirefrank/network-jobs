#!/usr/bin/env bash
# Fetch a URL, save body + metadata under a triage fetch-log, print body path.
set -euo pipefail

URL="${1:-}"
TRIAGE_DIR="${2:-}"
LABEL="${3:-page}"

if [[ -z "$URL" || -z "$TRIAGE_DIR" ]]; then
  echo "Usage: fetch-page.sh <url> <triage-dir> [label]" >&2
  exit 1
fi

mkdir -p "$TRIAGE_DIR/fetch-log"
TS="$(date -u +%Y%m%dT%H%M%SZ)"
BODY="$TRIAGE_DIR/fetch-log/${TS}-${LABEL}.body"
META="$TRIAGE_DIR/fetch-log/${TS}-${LABEL}.json"

CODE=0
HTTP_CODE="$(curl -sS -L --max-time 60 -A 'Mozilla/5.0 (compatible; NetworkJobs/1.0)' \
  -o "$BODY" -w '%{http_code}' "$URL")" || CODE=$?

python3 - "$META" "$URL" "$HTTP_CODE" "$CODE" "$BODY" <<'PY'
import json, sys
from datetime import datetime, timezone
meta_path, url, http_code, curl_code, body = sys.argv[1:]
doc = {
  "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
  "method": "curl",
  "url": url,
  "status": int(http_code) if http_code.isdigit() else None,
  "curlExit": int(curl_code),
  "bodyPath": body,
  "disposition": "staged",
  "notes": "",
}
open(meta_path, "w").write(json.dumps(doc, indent=2) + "\n")
print(body)
PY
