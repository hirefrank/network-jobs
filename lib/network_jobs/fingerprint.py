"""Stable job identity: ATS id when present, else company+title+location."""

from __future__ import annotations

import hashlib
import re
from typing import Any

from .locations import parse_locations
from .text import collapse_ws, normalize_company, normalize_title

UUID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
    re.I,
)
# Our corpus ids look like "stripe-senior-backend-engineer-ab12"
SLUG_ID_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+){2,}$")


def location_key(job: dict[str, Any]) -> str:
    parsed = parse_locations(job)
    if parsed:
        bits = []
        for loc in parsed:
            if loc.get("remote"):
                bits.append("remote")
            city = collapse_ws(str(loc.get("city") or "")).lower()
            region = collapse_ws(str(loc.get("region") or "")).lower()
            raw = collapse_ws(str(loc.get("raw") or "")).lower()
            bit = city or region or raw or (loc.get("bucket") or "")
            if bit and bit not in bits:
                bits.append(bit)
        if bits:
            return "|".join(sorted(bits))
    return collapse_ws(str(job.get("location") or "")).lower()


def ats_id(job: dict[str, Any]) -> str | None:
    for key in ("externalId", "atsId", "jobId", "requisitionId", "gh_jid"):
        value = job.get(key)
        if value is None:
            continue
        text = collapse_ws(str(value))
        if text and not text.lower().startswith("http"):
            return text
    value = job.get("id")
    if value is None:
        return None
    text = collapse_ws(str(value))
    if not text or text.lower().startswith("http"):
        return None
    if text.isdigit() and len(text) >= 3:
        return text
    if UUID_RE.match(text):
        return text
    # Skip our own corpus slugs and fingerprints
    if text.startswith("id:") or text.startswith("fp:"):
        return None
    if SLUG_ID_RE.match(text) and any(c.isalpha() for c in text) and text.count("-") >= 2:
        return None
    if re.fullmatch(r"[A-Za-z0-9_-]{4,64}", text):
        return text
    return None


def fingerprint(job: dict[str, Any], company: str | None = None) -> str:
    existing = job.get("fingerprint")
    if isinstance(existing, str) and existing.startswith(("id:", "fp:")):
        return existing
    company_n = normalize_company(company or str(job.get("company") or ""))
    ext = ats_id(job)
    if ext:
        return f"id:{company_n}:{ext}"
    title_n = normalize_title(str(job.get("title") or ""))
    loc_n = location_key(job)
    basis = f"{company_n}|{title_n}|{loc_n}"
    digest = hashlib.sha1(basis.encode("utf-8")).hexdigest()[:12]
    return f"fp:{company_n}:{digest}"


def listing_set_hash(jobs: list[dict[str, Any]], company: str | None = None) -> str:
    fps = sorted({fingerprint(j, company=company) for j in jobs})
    blob = "\n".join(fps).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()[:16]
