#!/usr/bin/env bash
# Parse LinkedIn Connections ZIP/CSV → ~/.network-jobs connections + companies.
set -euo pipefail

usage() {
  cat <<'EOF'
Usage: parse-linkedin.sh <zip-or-csv> [--out DIR] [--min-count N]

Writes:
  DIR/connections/connections.json
  DIR/companies/companies.json
  DIR/logs/import-<timestamp>.json
EOF
  exit 1
}

INPUT="${1:-}"
[[ -n "$INPUT" && "$INPUT" != "-h" && "$INPUT" != "--help" ]] || usage
shift || true

OUT="${NETWORK_JOBS_HOME:-$HOME/.network-jobs}"
MIN_COUNT=1

while [[ $# -gt 0 ]]; do
  case "$1" in
    --out) OUT="$2"; shift 2 ;;
    --min-count) MIN_COUNT="$2"; shift 2 ;;
    *) echo "Unknown arg: $1"; usage ;;
  esac
done

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ASSET_DIR="$(cd "$SCRIPT_DIR/../assets" && pwd)"

mkdir -p "$OUT/connections" "$OUT/companies" "$OUT/config" "$OUT/logs"

# Ensure config ignore lists exist
for f in companies-to-ignore.json company-words-to-ignore.json company-overrides.json; do
  if [[ ! -f "$OUT/config/$f" ]]; then
    cp "$ASSET_DIR/$f" "$OUT/config/$f"
  fi
done

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

CSV=""
if [[ "$INPUT" == *.zip || "$INPUT" == *.ZIP ]]; then
  unzip -q -o "$INPUT" -d "$TMP"
  # LinkedIn nests Connections.csv variously
  CSV="$(find "$TMP" -type f \( -iname 'Connections.csv' -o -iname 'connections.csv' \) | head -n1 || true)"
  if [[ -z "$CSV" ]]; then
    echo "ERROR: Connections.csv not found inside ZIP" >&2
    find "$TMP" -type f | head -40 >&2
    exit 1
  fi
elif [[ "$INPUT" == *.csv || "$INPUT" == *.CSV ]]; then
  CSV="$INPUT"
else
  echo "ERROR: expected .zip or .csv, got: $INPUT" >&2
  exit 1
fi

export PARSE_CSV="$CSV"
export PARSE_OUT="$OUT"
export PARSE_MIN_COUNT="$MIN_COUNT"
export PARSE_IGNORE_COMPANIES="$OUT/config/companies-to-ignore.json"
export PARSE_IGNORE_WORDS="$OUT/config/company-words-to-ignore.json"
export PARSE_OVERRIDES="$OUT/config/company-overrides.json"

python3 <<'PY'
import csv, json, os, re, hashlib
from datetime import datetime, timezone
from pathlib import Path

csv_path = Path(os.environ["PARSE_CSV"])
out = Path(os.environ["PARSE_OUT"])
min_count = int(os.environ["PARSE_MIN_COUNT"])

def load_json(path, default):
    p = Path(path)
    if not p.exists():
        return default
    with p.open() as f:
        return json.load(f)

ignore_companies_raw = load_json(os.environ["PARSE_IGNORE_COMPANIES"], [])
ignore_words_raw = load_json(os.environ["PARSE_IGNORE_WORDS"], [])
overrides_raw = load_json(os.environ["PARSE_OVERRIDES"], [])

SUFFIX_RE = re.compile(
    r"\b(inc|incorporated|corp|corporation|llc|ltd|limited|llp|lp|plc|co|company|group|holdings|worldwide|international|global|technologies|technology|solutions|services)\b",
    re.I,
)
PUNCT_RE = re.compile(r"[.,/#!$%^&*;:{}=\-_`~()•]")

def basic_normalize(name: str) -> str:
    s = name.lower()
    s = PUNCT_RE.sub(" ", s)
    s = SUFFIX_RE.sub(" ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s

ignore_companies = {basic_normalize(x) for x in ignore_companies_raw}
ignore_words = {w.lower() for w in ignore_words_raw}
overrides = {
    basic_normalize(o["linkedinName"]): basic_normalize(o["matchTo"])
    for o in overrides_raw
    if isinstance(o, dict) and "linkedinName" in o and "matchTo" in o
}

def normalize(name: str) -> str:
    n = basic_normalize(name)
    return overrides.get(n, n)

def should_ignore(name: str) -> bool:
    n = normalize(name)
    if not n:
        return True
    if n in ignore_companies:
        return True
    for w in ignore_words:
        if w in n:
            return True
    return False

def slugify(normalized: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", normalized).strip("-")
    return s or "unknown"

# Read CSV — LinkedIn may prepend notes before the header
raw = csv_path.read_text(encoding="utf-8-sig", errors="replace").splitlines()
header_idx = None
for i, line in enumerate(raw):
    low = line.lower()
    if "first name" in low and "company" in low:
        header_idx = i
        break
if header_idx is None:
    raise SystemExit("ERROR: could not find Connections CSV header (First Name + Company)")

reader = csv.DictReader(raw[header_idx:])
# Normalize header keys
def get(row, *keys):
    lower = { (k or "").lower().strip(): v for k, v in row.items() }
    for key in keys:
        for lk, v in lower.items():
            if key == lk or key in lk:
                return (v or "").strip()
    return ""

connections = []
for row in reader:
    company = get(row, "company")
    if not company:
        continue
    connections.append({
        "firstName": get(row, "first name"),
        "lastName": get(row, "last name"),
        "company": company,
        "position": get(row, "position"),
        "url": get(row, "url") or None,
        "email": get(row, "email address", "email") or None,
        "connectedOn": get(row, "connected on", "connected") or None,
    })

# Aggregate companies
companies_map = {}
kept_connections = []
ignored = 0
for c in connections:
    if should_ignore(c["company"]):
        ignored += 1
        continue
    kept_connections.append(c)
    norm = normalize(c["company"])
    entry = companies_map.get(norm)
    person = {
        "name": f"{c['firstName']} {c['lastName']}".strip(),
        "position": c["position"],
        "url": c["url"],
    }
    if entry is None:
        companies_map[norm] = {
            "name": c["company"],
            "normalized": norm,
            "slug": slugify(norm),
            "domain": "",
            "connectionCount": 1,
            "people": [person] if person["name"] else [],
        }
    else:
        entry["connectionCount"] += 1
        if person["name"] and len(entry["people"]) < 10:
            entry["people"].append(person)

companies = sorted(
    companies_map.values(),
    key=lambda x: (-x["connectionCount"], x["name"].lower()),
)
if min_count > 1:
    companies = [c for c in companies if c["connectionCount"] >= min_count]

(out / "connections" / "connections.json").write_text(
    json.dumps(kept_connections, indent=2, ensure_ascii=False) + "\n"
)
(out / "companies" / "companies.json").write_text(
    json.dumps(companies, indent=2, ensure_ascii=False) + "\n"
)

ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
summary = {
    "timestamp": ts,
    "source": str(csv_path),
    "rawConnectionsWithCompany": len(connections),
    "keptConnections": len(kept_connections),
    "ignoredConnections": ignored,
    "companies": len(companies),
    "minCount": min_count,
    "topCompanies": [
        {"name": c["name"], "count": c["connectionCount"]} for c in companies[:20]
    ],
}
(out / "logs" / f"import-{ts}.json").write_text(json.dumps(summary, indent=2) + "\n")
print(json.dumps(summary, indent=2))
PY
