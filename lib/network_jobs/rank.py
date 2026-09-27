"""Local ranker over corpus shards + prefs + résumé keywords."""

from __future__ import annotations

import json
import re
from datetime import date, datetime
from pathlib import Path
from typing import Any

from .paths import data_home
from .prefs import load_resume_keywords, name_tokens, score_job

DEFAULT_K = 25

#: Postings older than this (by postedAt) are flagged stale and hidden by default.
STALE_POSTED_DAYS = 90
#: Without a postedAt we can't judge posting age; fall back to crawl freshness.
STALE_UNSEEN_DAYS = 120
#: Fresh postings get a small, explainable boost so new roles surface first.
RECENT_BOOST_DAYS = 14
RECENT_BOOST = 2.0
SEMI_RECENT_BOOST_DAYS = 30
SEMI_RECENT_BOOST = 1.0


def _parse_posted_date(raw: Any) -> date | None:
    """Best-effort postedAt → date. ATS formats vary wildly; None when unknown."""
    if not raw:
        return None
    s = str(raw).strip()
    m = re.match(r"^(\d{4})-(\d{2})-(\d{2})", s)
    if m:
        try:
            return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        except ValueError:
            return None
    for fmt in ("%Y/%m/%d", "%m/%d/%Y", "%b %d, %Y", "%B %d, %Y"):
        try:
            return datetime.strptime(s[:24], fmt).date()
        except ValueError:
            continue
    return None


def posting_age_days(raw: Any, today: date | None = None) -> int | None:
    """Age in days of a postedAt/lastSeen-style value; None when unparseable."""
    d = _parse_posted_date(raw)
    if d is None:
        return None
    today = today or date.today()
    return max(0, (today - d).days)


def job_is_stale(job: dict[str, Any], today: date | None = None) -> bool:
    """A posting is stale when the posting itself is old, or when we have no
    postedAt and haven't confirmed the listing in a long time."""
    today = today or date.today()
    posted_age = posting_age_days(job.get("postedAt"), today)
    if posted_age is not None:
        return posted_age > STALE_POSTED_DAYS
    seen_age = posting_age_days(job.get("lastSeen") or job.get("firstSeen"), today)
    return seen_age is not None and seen_age > STALE_UNSEEN_DAYS


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
    # Seniority is a soft scoring signal, not a shard filter: always load
    # both senior and mid shards and let score_job rank them. (Interns live
    # in mid shards, staff+ in senior shards.) Filtering here used to hide
    # "mid"-classified roles — e.g. plain-titled "Product Manager" postings —
    # from senior seekers before scoring ever saw them.
    sens = ["senior", "mid"]

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


def _semantic_context(
    corpus: Path,
    jobs: list[dict[str, Any]],
    resume_text: str,
    query: str | None,
) -> tuple[list[float] | None, list[float] | None, dict[str, list[float]]]:
    """Embed résumé + query once per run; resolve cached job vectors by fp.

    Returns (resume_vector, query_vector, {fingerprint: vector}). Everything
    is None/{} when no embedding provider is available, in which case callers
    fall back to keyword scoring with unchanged scores.
    """
    from .embeddings import get_provider, load_embeddings_cache
    from .fingerprint import fingerprint as _fingerprint

    provider = get_provider()
    if provider is None:
        return None, None, {}
    cache = load_embeddings_cache(corpus)
    cached = cache.get("vectors") or {}
    job_vectors: dict[str, list[float]] = {}
    for job in jobs:
        fp = _fingerprint(job)
        vec = cached.get(fp)
        if vec:
            job_vectors[fp] = vec
    texts: list[str] = []
    kinds: list[str] = []
    if (resume_text or "").strip():
        texts.append(resume_text.strip())
        kinds.append("resume")
    if (query or "").strip():
        texts.append(query.strip())
        kinds.append("query")
    vecs = provider.embed(texts) if texts else None
    by_kind = dict(zip(kinds, vecs)) if vecs else {}
    return by_kind.get("resume"), by_kind.get("query"), job_vectors


def rank_corpus(
    data_dir: str | Path | None = None,
    k: int = DEFAULT_K,
    query: str | None = None,
    prefs: dict[str, Any] | None = None,
    resume_text: str | None = None,
    include_stale: bool = False,
    today: date | str | None = None,
) -> dict[str, Any]:
    root = data_home(data_dir)
    corpus = root / "corpus"
    if isinstance(today, str):
        today = date.fromisoformat(today[:10])
    today_d = today or date.today()
    if prefs is None:
        raw = _read_json(root / "preferences.json")
        prefs = raw if isinstance(raw, dict) else {}
    if resume_text is None:
        resume_path = root / "resume" / "text.md"
        resume_text = resume_path.read_text() if resume_path.is_file() else ""
    profile = _read_json(root / "profile.json") or {}
    keywords = load_resume_keywords(resume_text, exclude=name_tokens(profile)) if resume_text else []
    jobs, shard_files = _iter_shards(corpus, prefs, query)
    # Opt-in semantic signals: résumé vector replaces the keyword `resume`
    # bonus; query vector adds a small boost on top of lexical `query` hits.
    # No provider -> all None/{}, scores identical to before.
    resume_vector, query_vector, job_vectors = _semantic_context(
        corpus, jobs, resume_text, query
    )
    from .fingerprint import fingerprint as _fingerprint

    fps = [_fingerprint(j) for j in jobs]
    scored = [
        score_job(
            j,
            prefs,
            resume_keywords=keywords,
            resume_vector=resume_vector,
            job_vector=job_vectors.get(fp),
        )
        for j, fp in zip(jobs, fps)
    ]
    scored = [j for j in scored if not j.get("veto")]
    stale_hidden = 0
    fresh: list[dict[str, Any]] = []
    for job in scored:
        if job_is_stale(job, today_d):
            job["stale"] = True
            stale_hidden += 1
            continue
        age = posting_age_days(job.get("postedAt"), today_d)
        if age is not None and age <= RECENT_BOOST_DAYS:
            job["matchScore"] = round(float(job.get("matchScore") or 0) + RECENT_BOOST, 2)
            job.setdefault("matchReasons", []).append("recent")
        elif age is not None and age <= SEMI_RECENT_BOOST_DAYS:
            job["matchScore"] = round(float(job.get("matchScore") or 0) + SEMI_RECENT_BOOST, 2)
            job.setdefault("matchReasons", []).append("recent")
        fresh.append(job)
    if include_stale:
        scored = fresh + [j for j in scored if j.get("stale")]
    else:
        scored = fresh
    if query:
        from .embeddings import (
            QUERY_SEMANTIC_FLOOR,
            QUERY_SEMANTIC_MAX,
            cosine,
            semantic_bonus,
        )

        q = query.lower()
        q_tokens = [t for t in q.replace("/", " ").split() if len(t) > 2]
        for job in scored:
            blob = f"{job.get('title')} {job.get('department')} {job.get('company')}".lower()
            hits = sum(1 for t in q_tokens if t in blob)
            job["matchScore"] = float(job.get("matchScore") or 0) + hits * 2
            if hits:
                job.setdefault("matchReasons", []).append("query")
            if query_vector is not None:
                # Semantic query boost: additive, never replaces lexical hits.
                qv = job_vectors.get(_fingerprint(job))
                if qv is not None:
                    qb = semantic_bonus(
                        cosine(query_vector, qv),
                        QUERY_SEMANTIC_FLOOR,
                        QUERY_SEMANTIC_MAX,
                    )
                    if qb > 0:
                        job["matchScore"] = float(job.get("matchScore") or 0) + qb
                        job.setdefault("matchReasons", []).append("query-semantic")
    # Stable multi-pass sort: stale sinks to the bottom, then score desc,
    # then most-recently-seen first, then title.
    scored.sort(key=lambda j: str(j.get("title") or ""))
    scored.sort(key=lambda j: str(j.get("lastSeen") or ""), reverse=True)
    scored.sort(key=lambda j: (bool(j.get("stale")), -float(j.get("matchScore") or 0)))
    n = len(scored)
    k_eff = max(0, min(int(k), n))
    top = scored[:k_eff]
    return {
        "k": k_eff,
        "n": n,
        "showing": f"{k_eff} of {n}",
        "query": query or "",
        "shards": sorted(set(shard_files)),
        "staleHidden": 0 if include_stale else stale_hidden,
        "jobs": top,
    }
