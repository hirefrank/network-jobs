"""Score staged listings against preferences.json."""

from __future__ import annotations

from collections import Counter
from typing import Any

from .classify import classify_job
from .embeddings import (
    RESUME_SEMANTIC_FLOOR,
    RESUME_SEMANTIC_MAX,
    cosine,
    semantic_bonus,
)
from .fingerprint import fingerprint
from .locations import city_matches, location_buckets_for
from .text import former_employer_match, tokenize


def name_tokens(profile: dict[str, Any] | None) -> set[str]:
    """Tokens from the user's name, so résumé keywords don't echo "ada lovelace"."""
    return set(tokenize(str((profile or {}).get("name") or "")))


#: Generic résumé filler that pollutes keyword extraction without describing the
#: actual work. Kept deliberately small; STOPWORDS covers articles/prepositions.
RESUME_NOISE = frozenset({
    "new", "novel", "various", "multiple", "many", "much", "several",
    "work", "worked", "working", "works", "job", "role", "team", "teams",
    "use", "used", "using", "usage", "via", "across", "within",
    "including", "include", "etc", "highly", "strong", "proven",
    "track", "record", "helped", "helping", "led", "leading",
    "drive", "driving", "built", "building", "also", "well",
    "day", "month", "year", "years", "end",
})


def load_resume_keywords(
    text: str,
    limit: int = 40,
    exclude: set[str] | None = None,
) -> list[str]:
    from .text import STOPWORDS
    import re

    words = [w.lower() for w in re.findall(r"[A-Za-z][A-Za-z0-9+\-/#]{2,}", text or "")]
    drop = set(STOPWORDS) | set(RESUME_NOISE)
    if exclude:
        drop |= {w.lower() for w in exclude}
    words = [w for w in words if w not in drop]
    return [w for w, _ in Counter(words).most_common(limit)]


def _work_modes(prefs: dict[str, Any]) -> set[str]:
    return {str(m).lower() for m in (prefs.get("workModes") or [])}


def location_matches_prefs(job: dict[str, Any], prefs: dict[str, Any]) -> tuple[bool, list[str]]:
    reasons: list[str] = []
    modes = _work_modes(prefs)
    buckets = set(location_buckets_for(job))
    pref_buckets = {str(b).lower() for b in (prefs.get("locationBuckets") or [])}
    onsite_places = [str(x) for x in (prefs.get("onsiteLocations") or [])]
    loc_places = [str(x) for x in (prefs.get("locations") or [])]

    remote_ok = (not modes or "remote" in modes) and "remote" in buckets
    if remote_ok:
        reasons.append("remote")

    onsite_ok = False
    if modes & {"hybrid", "onsite"} or (not modes and pref_buckets - {"remote"}):
        if onsite_places and city_matches(job, onsite_places):
            onsite_ok = True
            reasons.append("onsiteLocations")
        elif not onsite_places and city_matches(job, loc_places):
            onsite_ok = True
            reasons.append("locations")
        elif pref_buckets & (buckets - {"remote"}):
            onsite_ok = True
            reasons.append("locationBucket")

    if not modes and not pref_buckets and not onsite_places and not loc_places:
        return True, ["no-location-prefs"]

    if remote_ok or onsite_ok:
        return True, reasons

    # Query-less default: if they only listed remote, do not leak global onsite.
    if modes == {"remote"}:
        return False, []
    if pref_buckets and buckets & pref_buckets:
        return True, ["locationBucket"]
    return False, []


def _keyword_hit(text: str, phrases: list[str] | None) -> list[str]:
    blob = (text or "").lower()
    hits = []
    for phrase in phrases or []:
        p = phrase.lower().strip()
        if p and p in blob:
            hits.append(phrase)
    return hits


def score_job(
    job: dict[str, Any],
    prefs: dict[str, Any] | None,
    resume_keywords: list[str] | None = None,
    company: str | None = None,
    resume_vector: list[float] | None = None,
    job_vector: list[float] | None = None,
) -> dict[str, Any]:
    """Score one job against prefs.

    resume_vector/job_vector activate the semantic résumé signal: when both
    are present, cosine similarity *replaces* the keyword `resume` bonus
    (never stacks with it). Absent either vector, keyword scoring runs
    exactly as before.
    """
    prefs = prefs or {}
    classified = classify_job(job, company=company or job.get("company"))
    title = str(classified.get("title") or "")
    dept = str(classified.get("department") or "")
    blob = f"{title} {dept} {classified.get('company') or ''}"
    score = 0.0
    reasons: list[str] = []
    veto = False
    hard_fail = False

    deal = _keyword_hit(blob, prefs.get("dealBreakers"))
    if deal:
        veto = True
        reasons.append(f"dealBreaker:{deal[0]}")

    policy = str(prefs.get("formerEmployerPolicy") or "").lower()
    if policy == "exclude" and former_employer_match(
        str(classified.get("company") or ""), prefs.get("formerEmployers") or []
    ):
        veto = True
        reasons.append("formerEmployer")

    loc_ok, loc_reasons = location_matches_prefs(classified, prefs)
    location_required = bool(_work_modes(prefs) or prefs.get("locationBuckets") or prefs.get("onsiteLocations"))
    if loc_ok:
        score += 4
        reasons.extend(loc_reasons)
    elif location_required:
        score -= 3
        hard_fail = True

    cats = [str(c).lower() for c in (prefs.get("categories") or [])]
    if cats:
        if classified.get("category") in cats:
            score += 5
            reasons.append("category")
        else:
            score -= 1
            hard_fail = True

    sen_prefs = [str(s).lower() for s in (prefs.get("seniority") or [])]
    signals = [str(s).lower() for s in (classified.get("senioritySignals") or [])]
    seniority = str(classified.get("seniority") or "mid")
    staff_pref = "staff+" in sen_prefs or any("staff" in s for s in sen_prefs)
    intern_pref = "intern" in sen_prefs or any("intern" in s for s in sen_prefs)

    if "intern" in signals and not intern_pref and sen_prefs:
        hard_fail = True
        reasons.append("intern-mismatch")
    elif intern_pref and "intern" in signals:
        score += 4
        reasons.append("intern")
    elif "junior" in signals and sen_prefs and not intern_pref and not staff_pref:
        # Positive junior signal ("Associate", "Junior", "Entry-Level") is a
        # real mismatch for senior/staff seekers — same treatment as intern.
        hard_fail = True
        reasons.append("junior-mismatch")
    elif staff_pref:
        if "staff+" in signals:
            score += 4
            reasons.append("staff+")
        else:
            # Soft: a staff seeker may still want a strong senior role.
            score -= 2
            reasons.append("staff-mismatch")
    elif sen_prefs and seniority in sen_prefs:
        score += 3
        reasons.append("seniority")
    elif sen_prefs and "unmarked" in signals:
        # Level-ambiguous title ("Product Manager", "Software Engineer"):
        # neither bonus nor penalty — never exclude on seniority alone.
        reasons.append("seniority-ambiguous")
    elif sen_prefs:
        score -= 2
        reasons.append("seniority-mismatch")

    track_prefs = [str(t).lower() for t in (prefs.get("track") or [])]
    track = str(classified.get("track") or "ic")
    if track_prefs and "either" not in track_prefs:
        if track in track_prefs:
            score += 3
            reasons.append("track")
        else:
            score -= 2
            hard_fail = True

    must = _keyword_hit(blob, prefs.get("mustHaves"))
    if must:
        score += 2
        reasons.append("mustHave")

    if resume_keywords:
        if resume_vector is not None and job_vector is not None:
            # Semantic résumé signal replaces the keyword bonus entirely.
            bonus = semantic_bonus(
                cosine(resume_vector, job_vector),
                RESUME_SEMANTIC_FLOOR,
                RESUME_SEMANTIC_MAX,
            )
            if bonus > 0:
                score += bonus
                reasons.append("resume-semantic")
        else:
            tokens = set(tokenize(blob))
            hits = [k for k in resume_keywords if k.lower() in tokens or k.lower() in blob.lower()]
            if hits:
                score += min(4, len(hits))
                reasons.append("resume")

    salary_min = prefs.get("salaryMin")
    salary = classified.get("salary") or {}
    if isinstance(salary_min, (int, float)) and isinstance(salary, dict):
        lo = salary.get("min") or salary.get("max")
        if isinstance(lo, (int, float)):
            if lo >= salary_min:
                score += 1
                reasons.append("salary")
            else:
                score -= 2

    matched = (not veto) and (not hard_fail)
    # Empty prefs: treat everything as a match so discover still shortlists.
    empty_prefs = not prefs or not any(
        prefs.get(k) for k in (
            "categories", "workModes", "locationBuckets", "onsiteLocations",
            "seniority", "track", "mustHaves", "dealBreakers",
        )
    )
    if empty_prefs:
        matched = not veto
        if not reasons:
            reasons.append("no-prefs")

    out = dict(classified)
    out["matchScore"] = round(score, 2)
    out["matchReasons"] = reasons
    out["matched"] = matched
    out["veto"] = veto
    return out


def match_listings(
    listings: list[dict[str, Any]],
    prefs: dict[str, Any] | None,
    resume_keywords: list[str] | None = None,
    company: str | None = None,
    resume_vector: list[float] | None = None,
    job_vectors: dict[str, list[float]] | None = None,
) -> dict[str, Any]:
    job_vectors = job_vectors or {}

    def _job_vector(job: dict[str, Any]) -> list[float] | None:
        fp = str(job.get("fingerprint") or "") or fingerprint(
            job, company=company or job.get("company")
        )
        return job_vectors.get(fp)

    scored = [
        score_job(
            j,
            prefs,
            resume_keywords=resume_keywords,
            company=company,
            resume_vector=resume_vector,
            job_vector=_job_vector(j),
        )
        for j in listings
    ]
    matches = [j for j in scored if j.get("matched")]
    matches.sort(key=lambda j: (-float(j.get("matchScore") or 0), str(j.get("title") or "")))
    depts = Counter(str(j.get("department") or "(none)") for j in listings)
    return {
        "nListings": len(listings),
        "nMatches": len(matches),
        "showing": f"{len(matches)} of {len(listings)} match prefs",
        "departments": dict(depts.most_common()),
        "jobs": matches,
        "allScored": scored,
    }
