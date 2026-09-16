"""Merge corpus jobs by fingerprint; expire unseen only when pagination is complete."""

from __future__ import annotations

import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .fingerprint import fingerprint
from .locations import location_buckets_for, primary_location_bucket
from .text import normalize_company, slugify

SHARD_SKIP = {"manifest.json", "jobs-all.json"}


def _today() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load_jobs(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    data = json.loads(path.read_text())
    if not isinstance(data, list):
        raise SystemExit(f"{path} must be a JSON array")
    return data


def job_fingerprint(job: dict[str, Any]) -> str:
    fp = fingerprint(job)
    job["fingerprint"] = fp
    return fp


def load_existing_jobs(corpus: Path) -> list[dict[str, Any]]:
    existing_path = corpus / "jobs-all.json"
    if existing_path.exists():
        existing = load_jobs(existing_path)
        if existing:
            return existing
    by_fp: dict[str, dict[str, Any]] = {}
    shard_names: set[str] = set()
    manifest_path = corpus / "manifest.json"
    if manifest_path.exists():
        try:
            manifest = json.loads(manifest_path.read_text())
            for meta in (manifest.get("categories") or {}).values():
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
    for path in corpus.glob("*.json"):
        if path.name in SHARD_SKIP:
            continue
        shard_names.add(path.name)
    for name in sorted(shard_names):
        path = corpus / name
        if not path.exists():
            continue
        for job in load_jobs(path):
            by_fp[job_fingerprint(job)] = job
    return list(by_fp.values())


def _company_key(job: dict[str, Any]) -> str:
    return normalize_company(str(job.get("company") or ""))


def merge_jobs(
    existing: list[dict[str, Any]],
    incoming: list[dict[str, Any]],
    *,
    expire_company: str | None = None,
    pagination_complete: bool = False,
) -> list[dict[str, Any]]:
    by_fp: dict[str, dict[str, Any]] = {}
    for job in existing:
        fp = job_fingerprint(job)
        by_fp[fp] = job
    seen: set[str] = set()
    today = _today()
    for job in incoming:
        fp = job_fingerprint(job)
        seen.add(fp)
        prev = by_fp.get(fp)
        merged = dict(job)
        if prev:
            if not merged.get("firstSeen"):
                merged["firstSeen"] = prev.get("firstSeen") or today
            if prev.get("url") and not merged.get("url"):
                merged["url"] = prev.get("url")
        else:
            merged.setdefault("firstSeen", today)
        merged["lastSeen"] = merged.get("lastSeen") or today
        merged["status"] = merged.get("status") or "open"
        if merged["status"] == "closed":
            merged["status"] = "open"
            merged.pop("closedAt", None)
        by_fp[fp] = merged

    if expire_company and pagination_complete:
        target = normalize_company(expire_company) or slugify(expire_company)
        for fp, job in list(by_fp.items()):
            if fp in seen:
                continue
            key = _company_key(job)
            slug = slugify(key)
            if key != target and slug != slugify(target) and slug != target:
                continue
            if str(job.get("status") or "open") == "closed":
                continue
            closed = dict(job)
            closed["status"] = "closed"
            closed["closedAt"] = today
            by_fp[fp] = closed
    elif expire_company and not pagination_complete:
        # Explicit no-op: incomplete crawls must not close unseen roles.
        pass

    return list(by_fp.values())


def write_shards(corpus: Path, jobs: list[dict[str, Any]]) -> dict[str, Any]:
    corpus.mkdir(parents=True, exist_ok=True)
    open_jobs = [j for j in jobs if str(j.get("status") or "open") != "closed"]
    categories: dict[str, list] = defaultdict(list)
    granular: dict[tuple[str, str, str], list] = defaultdict(list)
    for job in open_jobs:
        cat = job.get("category") or "other"
        buckets = job.get("locationBuckets") or [job.get("locationBucket") or "other"]
        if not isinstance(buckets, list) or not buckets:
            buckets = location_buckets_for(job)
        sen = job.get("seniority") or "mid"
        if sen not in ("senior", "mid"):
            sen = "mid"
        job.setdefault("locationBucket", primary_location_bucket(job))
        categories[cat].append(job)
        for loc in buckets:
            granular[(cat, loc or "other", sen)].append(job)

    written: set[str] = set()
    for cat, items in categories.items():
        name = f"{cat}.json"
        (corpus / name).write_text(json.dumps(items, indent=2, ensure_ascii=False) + "\n")
        written.add(name)
    for (cat, loc, sen), items in granular.items():
        name = f"{cat}-{loc}-{sen}.json"
        (corpus / name).write_text(json.dumps(items, indent=2, ensure_ascii=False) + "\n")
        written.add(name)
    (corpus / "jobs-all.json").write_text(json.dumps(jobs, indent=2, ensure_ascii=False) + "\n")
    written.add("jobs-all.json")

    now = _now()
    manifest: dict[str, Any] = {"lastUpdated": now, "totalJobs": len(open_jobs), "categories": {}}
    for cat, items in sorted(categories.items()):
        by_loc: dict[str, dict[str, list]] = defaultdict(lambda: {"senior": [], "mid": []})
        for job in items:
            buckets = job.get("locationBuckets") or [job.get("locationBucket") or "other"]
            sen = job.get("seniority") or "mid"
            if sen not in ("senior", "mid"):
                sen = "mid"
            for loc in buckets:
                by_loc[loc or "other"][sen].append(job)
        entry = {"count": len(items), "file": f"{cat}.json", "byLocation": {}}
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

    keep = written | SHARD_SKIP
    removed = []
    for path in corpus.glob("*.json"):
        if path.name in keep:
            continue
        path.unlink()
        removed.append(path.name)
    return {
        "totalJobs": len(open_jobs),
        "closedJobs": len(jobs) - len(open_jobs),
        "files": sorted(written),
        "removedStale": removed,
        "lastUpdated": now,
    }


def rebuild(
    incoming_path: Path,
    corpus: Path,
    *,
    expire_company: str | None = None,
    pagination_complete: bool = False,
) -> dict[str, Any]:
    incoming = load_jobs(incoming_path)
    existing = load_existing_jobs(corpus)
    jobs = merge_jobs(
        existing,
        incoming,
        expire_company=expire_company,
        pagination_complete=pagination_complete,
    )
    summary = write_shards(corpus, jobs)
    summary["incoming"] = len(incoming)
    summary["expired"] = bool(expire_company) and pagination_complete
    summary["expireCompany"] = expire_company or ""
    summary["paginationComplete"] = pagination_complete
    return summary
