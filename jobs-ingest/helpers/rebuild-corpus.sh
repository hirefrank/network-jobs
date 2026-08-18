#!/usr/bin/env bash
# Rebuild corpus shards + manifest from a flat jobs-all.json array.
# Merges with existing corpus/jobs-all.json (input wins on same URL).
set -euo pipefail

ALL_JSON="${1:-}"
if [[ -z "$ALL_JSON" || ! -f "$ALL_JSON" ]]; then
  echo "Usage: rebuild-corpus.sh <jobs-all.json>" >&2
  echo "  Merges into existing corpus (by URL); input jobs win on conflict." >&2
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
existing_path = corpus / "jobs-all.json"

def load_jobs(path: Path):
    if not path.exists():
        return []
    data = json.loads(path.read_text())
    if not isinstance(data, list):
        raise SystemExit(f"{path} must be a JSON array")
    return data

def load_existing_jobs() -> list:
    """Prefer jobs-all.json; if missing, reconstruct from category shard files."""
    if existing_path.exists():
        return load_jobs(existing_path)

    by_url = {}
    manifest_path = corpus / "manifest.json"
    shard_names = set()
    if manifest_path.exists():
        try:
            manifest = json.loads(manifest_path.read_text())
            for cat, meta in (manifest.get("categories") or {}).items():
                if isinstance(meta, dict) and meta.get("file"):
                    shard_names.add(meta["file"])
                for loc_meta in (meta.get("byLocation") or {}).values():
                    if not isinstance(loc_meta, dict):
                        continue
                    for sen_meta in loc_meta.values():
                        if isinstance(sen_meta, dict) and sen_meta.get("file"):
                            shard_names.add(sen_meta["file"])
        except json.JSONDecodeError:
            pass

    # Also scan category-only shards (engineering.json) if manifest incomplete
    for path in corpus.glob("*.json"):
        if path.name in {"manifest.json", "jobs-all.json"}:
            continue
        # Prefer category files (no location/seniority suffix pattern of 3+ parts
        # is fine — reading all non-reserved shards is safest for recovery)
        shard_names.add(path.name)

    for name in sorted(shard_names):
        path = corpus / name
        if not path.exists():
            continue
        for j in load_jobs(path):
            url = (j.get("url") or "").strip()
            if url:
                by_url[url] = j
    return list(by_url.values())

incoming = load_jobs(all_path)
# Merge: existing first, then incoming (incoming overwrites same URL)
by_url = {}
for j in load_existing_jobs():
    url = (j.get("url") or "").strip()
    if url:
        by_url[url] = j
for j in incoming:
    url = (j.get("url") or "").strip()
    if not url:
        continue
    prev = by_url.get(url)
    if prev and not j.get("firstSeen"):
        j = {**j, "firstSeen": prev.get("firstSeen") or j.get("firstSeen")}
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

written = set()

for cat, items in categories.items():
    name = f"{cat}.json"
    (corpus / name).write_text(json.dumps(items, indent=2, ensure_ascii=False) + "\n")
    written.add(name)

for (cat, loc, sen), items in granular.items():
    name = f"{cat}-{loc}-{sen}.json"
    (corpus / name).write_text(json.dumps(items, indent=2, ensure_ascii=False) + "\n")
    written.add(name)

(corpus / "jobs-all.json").write_text(
    json.dumps(jobs, indent=2, ensure_ascii=False) + "\n"
)
written.add("jobs-all.json")

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
written.add("manifest.json")

# Remove stale shard JSON files no longer referenced
keep = written | {"manifest.json", "jobs-all.json"}
removed = []
for path in corpus.glob("*.json"):
    if path.name in keep:
        continue
    # Only remove category / granular shard patterns
    if path.name == "manifest.json" or path.name == "jobs-all.json":
        continue
    path.unlink()
    removed.append(path.name)

print(json.dumps({
    "totalJobs": len(jobs),
    "incoming": len(incoming),
    "files": sorted(written),
    "removedStale": removed,
    "lastUpdated": now,
}, indent=2))
PY
