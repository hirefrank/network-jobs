"""Rank 1–2 intro roles and 1–2 forwarders from full connections.json.

Fetch job-description URLs only for the chosen roles. Department is enough
to draft when a JD fetch is skipped or blocked.
"""

from __future__ import annotations

from typing import Any

from .text import normalize_company, tokenize


def _person_name(row: dict[str, Any]) -> str:
    if row.get("name"):
        return str(row["name"]).strip()
    return f"{row.get('firstName') or ''} {row.get('lastName') or ''}".strip()


def _score_forwarder(job: dict[str, Any], person: dict[str, Any]) -> float:
    position = str(person.get("position") or "")
    blob = f"{job.get('title') or ''} {job.get('department') or ''} {job.get('category') or ''}"
    job_tokens = set(tokenize(blob))
    pos_tokens = set(tokenize(position))
    if not pos_tokens:
        return 0.5
    overlap = len(job_tokens & pos_tokens)
    score = overlap * 2.0
    # Light bonuses for same function words
    if job.get("track") == "manager" and any(t in pos_tokens for t in ("manager", "director", "head", "vp")):
        score += 2
    if job.get("category") == "product" and "product" in pos_tokens:
        score += 2
    if job.get("category") == "engineering" and any(t in pos_tokens for t in ("engineer", "engineering")):
        score += 2
    return score


def connections_at_company(connections: list[dict[str, Any]], company: str) -> list[dict[str, Any]]:
    want = normalize_company(company)
    if not want:
        return []
    hits = []
    for row in connections:
        if normalize_company(str(row.get("company") or "")) == want:
            hits.append(row)
    return hits


def rank_intros(
    jobs: list[dict[str, Any]],
    connections: list[dict[str, Any]],
    *,
    k_roles: int = 2,
    k_forwarders: int = 2,
) -> dict[str, Any]:
    open_jobs = [j for j in jobs if str(j.get("status") or "open") != "closed"]
    roles_out = []
    fetch_urls: list[str] = []
    for job in open_jobs[: max(0, k_roles)]:
        people = connections_at_company(connections, str(job.get("company") or ""))
        scored = []
        for person in people:
            scored.append({
                "name": _person_name(person),
                "position": person.get("position") or "",
                "url": person.get("url") or "",
                "email": person.get("email") or "",
                "score": round(_score_forwarder(job, person), 2),
            })
        scored.sort(key=lambda p: (-p["score"], p["name"]))
        forwarders = [p for p in scored if p["name"]][: max(0, k_forwarders)]
        url = str(job.get("url") or "")
        if url:
            fetch_urls.append(url)
        roles_out.append({
            "title": job.get("title"),
            "company": job.get("company"),
            "department": job.get("department") or "",
            "url": url,
            "category": job.get("category"),
            "track": job.get("track"),
            "fingerprint": job.get("fingerprint"),
            "forwarders": forwarders,
            "connectionCount": len(people),
        })
    return {
        "kRoles": len(roles_out),
        "kForwarders": k_forwarders,
        "showing": f"{len(roles_out)} roles, up to {k_forwarders} forwarders each",
        "fetchJdUrls": fetch_urls,
        "useDepartmentWithoutJd": True,
        "roles": roles_out,
    }
