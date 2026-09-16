"""Local ranker over corpus shards + prefs + résumé keywords."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .paths import data_home
from .prefs import load_resume_keywords, score_job

DEFAULT_K = 25


def _read_json(path: Path) -> Any:
    if not path.is_file():
        return None
    return json.loads(path.read_text())


def _iter_shards(corpus: Path, prefs: dict[str, Any], query: str | None) -> tuple[list[dict[str, Any]], list[str]]:
    manifest = _read_json(corpus / "manifest.json") or {}
    categories = (manifest.get("categories") or {}) if isinstance(manifest, dict) else {}
    wanted_cats = [str(c) for c in (prefs.get("categories") or [])]
    wanted_locs = [str(c) for c in (prefs.get("locationBuckets") or [])]
    wanted_sen = [str(s) for s in (prefs.get("seniority") or [])]
    if query:
        q = query.lower()
        if not wanted_cats:
            for cat in categories:
                if cat.replace("-", " ") in q or cat in q:
                    wanted_cats.append(cat)
        if "nyc" in q or "new york" in q:
            wanted_locs = list({*wanted_locs, "nyc"})
        if "sf" in q or "san francisco" in q or "bay area" in q:
            wanted_locs = list({*wanted_locs, "sf"})
        if "remote" in q:
            wanted_locs = list({*wanted_locs, "remote"})
        if "intern" in q:
            wanted_sen = list({*wanted_sen, "intern"})
        if "staff" in q or "principal" in q:
            wanted_sen = list({*wanted_sen, "staff+"})

    files: list[Path] = []
    cats = wanted_cats or list(categories.keys())
    locs = wanted_locs or ["nyc", "sf", "remote", "other"]
    sens = [s for s in wanted_sen if s in ("senior", "mid")] or ["senior", "mid"]

    for cat in cats:
        meta = categories.get(cat) or {}
        by_loc = meta.get("byLocation") or {}
        for loc in locs:
            loc_meta = by_loc.get(loc) or {}
            for sen in sens:
                info = loc_meta.get(sen) or {}
                fname = info.get("file")
                if fname:
                    files.append(corpus / fname)
        # Hybrid NYC-or-Remote lives in both shards; also pull category file if no granular hits
        if not files and meta.get("file"):
            files.append(corpus / str(meta["file"]))

    if not files:
        all_jobs = corpus / "jobs-all.json"
        if all_jobs.is_file():
            files.append(all_jobs)

    seen_files = []
    jobs: list[dict[str, Any]] = []
    seen_fp: set[str] = set()
    from .fingerprint import fingerprint

    for path in files:
        if not path.is_file() or path.name in {"manifest.json"}:
            continue
        seen_files.append(path.name)
        payload = _read_json(path)
        if not isinstance(payload, list):
            continue
        for job in payload:
            if str(job.get("status") or "open") == "closed":
                continue
            fp = fingerprint(job)
            if fp in seen_fp:
                continue
            seen_fp.add(fp)
            jobs.append(job)
    return jobs, seen_files


def rank_corpus(
    data_dir: str | Path | None = None,
    k: int = DEFAULT_K,
    query: str | None = None,
    prefs: dict[str, Any] | None = None,
    resume_text: str | None = None,
) -> dict[str, Any]:
    root = data_home(data_dir)
    corpus = root / "corpus"
    if prefs is None:
        raw = _read_json(root / "preferences.json")
        prefs = raw if isinstance(raw, dict) else {}
    if resume_text is None:
        resume_path = root / "resume" / "text.md"
        resume_text = resume_path.read_text() if resume_path.is_file() else ""
    keywords = load_resume_keywords(resume_text) if resume_text else []
    jobs, shard_files = _iter_shards(corpus, prefs, query)
    scored = [score_job(j, prefs, resume_keywords=keywords) for j in jobs]
    scored = [j for j in scored if not j.get("veto")]
    if query:
        q = query.lower()
        q_tokens = [t for t in q.replace("/", " ").split() if len(t) > 2]
        for job in scored:
            blob = f"{job.get('title')} {job.get('department')} {job.get('company')}".lower()
            hits = sum(1 for t in q_tokens if t in blob)
            job["matchScore"] = float(job.get("matchScore") or 0) + hits * 2
            if hits:
                job.setdefault("matchReasons", []).append("query")
    scored.sort(key=lambda j: (-float(j.get("matchScore") or 0), str(j.get("lastSeen") or ""), str(j.get("title") or "")))
    n = len(scored)
    k_eff = max(0, min(int(k), n))
    top = scored[:k_eff]
    return {
        "k": k_eff,
        "n": n,
        "showing": f"{k_eff} of {n}",
        "query": query or "",
        "shards": sorted(set(shard_files)),
        "jobs": top,
    }
