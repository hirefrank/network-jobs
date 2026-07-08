#!/usr/bin/env bash
# Rebuild corpus shards + manifest from a flat jobs-all.json array.
set -euo pipefail

ALL_JSON="${1:-}"
if [[ -z "$ALL_JSON" || ! -f "$ALL_JSON" ]]; then
  echo "Usage: rebuild-corpus.sh <jobs-all.json>" >&2
  exit 1
fi

DATA="${NETWORK_JOBS_HOME:-$HOME/.network-jobs}"
CORPUS="$DATA/corpus"
mkdir -p "$CORPUS"

export ALL_JSON CORPUS
python3 <<'PY'
import json, os, re
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

all_path = Path(os.environ["ALL_JSON"])
corpus = Path(os.environ["CORPUS"])

jobs = json.loads(all_path.read_text())
if not isinstance(jobs, list):
    raise SystemExit("jobs-all.json must be a JSON array")

# Dedupe by url (last wins)
by_url = {}
for j in jobs:
    url = (j.get("url") or "").strip()
    if not url:
        continue
    by_url[url] = j
jobs = list(by_url.values())

categories = defaultdict(list)
granular = defaultdict(list)

for j in jobs:
    cat = j.get("category") or "other"
    loc = j.get("locationBucket") or "other"
    sen = j.get("seniority") or "mid"
    categories[cat].append(j)
    granular[(cat, loc, sen)].append(j)

# Remove old shard jsons except we rewrite everything we know
# Keep non-matching files? Safer to only overwrite files we generate.
written = []

for cat, items in categories.items():
    path = corpus / f"{cat}.json"
    path.write_text(json.dumps(items, indent=2, ensure_ascii=False) + "\n")
    written.append(path.name)

for (cat, loc, sen), items in granular.items():
    name = f"{cat}-{loc}-{sen}.json"
    path = corpus / name
    path.write_text(json.dumps(items, indent=2, ensure_ascii=False) + "\n")
    written.append(name)

# Also write jobs-all for debugging
(corpus / "jobs-all.json").write_text(
    json.dumps(jobs, indent=2, ensure_ascii=False) + "\n"
)

now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
manifest = {
    "lastUpdated": now,
    "totalJobs": len(jobs),
    "categories": {},
}

for cat, items in sorted(categories.items()):
    by_loc = defaultdict(lambda: {"senior": [], "mid": []})
    for j in items:
        loc = j.get("locationBucket") or "other"
        sen = j.get("seniority") or "mid"
        if sen not in ("senior", "mid"):
            sen = "mid"
        by_loc[loc][sen].append(j)

    entry = {
        "count": len(items),
        "file": f"{cat}.json",
        "byLocation": {},
    }
    for loc, sens in sorted(by_loc.items()):
        entry["byLocation"][loc] = {}
        for sen, arr in sens.items():
            if not arr:
                continue
            fname = f"{cat}-{loc}-{sen}.json"
            entry["byLocation"][loc][sen] = {"count": len(arr), "file": fname}
    manifest["categories"][cat] = entry

(corpus / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
print(json.dumps({"totalJobs": len(jobs), "files": written, "lastUpdated": now}, indent=2))
PY
