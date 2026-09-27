"""Parse job locations into city/region plus corpus buckets.

Buckets stay the fast path. Hybrid strings like "New York, NY or Remote"
hit both `nyc` and `remote` so shard reads and onsiteLocations filtering work.
"""

from __future__ import annotations

import re
from typing import Any

from .text import collapse_ws

NYC_CITY = {
    "nyc", "new york", "new york city", "new york ny", "manhattan", "brooklyn",
    "queens", "bronx", "staten island", "hoboken", "jersey city", "long island city",
    "brooklyn ny", "manhattan ny",
}
SF_CITY = {
    "sf", "san francisco", "san francisco ca", "bay area", "sf bay area",
    "palo alto", "mountain view", "oakland", "berkeley", "sunnyvale",
    "san jose", "south bay", "redwood city", "menlo park", "cupertino",
    "san mateo", "foster city", "emeryville",
}
REMOTE_MARKERS = (
    "remote", "distributed", "work from home", "wfh", "anywhere",
    "remote-first", "remote first", "remote us", "remote-usa", "us remote",
)
SPLIT_RE = re.compile(r"\s*(?:/|;|\||\bor\b|\band\b|\+|•)\s*", re.I)


def _norm_place(value: str) -> str:
    s = collapse_ws(value).lower()
    s = re.sub(r"[()\[\].,]", " ", s)
    s = collapse_ws(s)
    return s


def _is_remote(text: str) -> bool:
    n = _norm_place(text)
    return any(m in n for m in REMOTE_MARKERS)


def _city_bucket(text: str) -> str | None:
    n = _norm_place(text)
    if not n:
        return None
    compact = n.replace(",", " ")
    compact = collapse_ws(compact)
    if compact in NYC_CITY or n in NYC_CITY:
        return "nyc"
    if compact in SF_CITY or n in SF_CITY:
        return "sf"
    for token, bucket, aliases in (
        ("nyc", "nyc", NYC_CITY),
        ("sf", "sf", SF_CITY),
    ):
        del token
        if any(alias in n for alias in aliases):
            return bucket
    if re.search(r"\bnew york\b", n) or re.search(r"\bnyc\b", n):
        return "nyc"
    if re.search(r"\bsan francisco\b", n) or re.search(r"\bbay area\b", n) or re.search(r"\bpalo alto\b", n):
        return "sf"
    return None


def _split_raw(raw: str) -> list[str]:
    raw = collapse_ws(raw)
    if not raw:
        return []
    parts = [p for p in SPLIT_RE.split(raw) if p and p.lower() not in {"and", "or"}]
    return parts or [raw]


def parse_one(raw: str) -> dict[str, Any]:
    text = collapse_ws(raw)
    remote = _is_remote(text)
    bucket = "remote" if remote and not _city_bucket(text) else (_city_bucket(text) or ("remote" if remote else "other"))
    city = None
    region = None
    if not remote or _city_bucket(text):
        # "New York, NY" / "San Francisco, CA"
        m = re.match(r"^([^,;/|]+)(?:,\s*([A-Za-z]{2,}))?", text)
        if m:
            city = collapse_ws(m.group(1))
            region = collapse_ws(m.group(2) or "")
            if _is_remote(city):
                city = None
                region = None
    if city and _is_remote(city):
        city = None
    return {
        "raw": text,
        "city": city or None,
        "region": region or None,
        "remote": remote,
        "bucket": bucket,
    }


def parse_locations(job: dict[str, Any]) -> list[dict[str, Any]]:
    raw_list = job.get("locations")
    parsed: list[dict[str, Any]] = []
    seen: set[str] = set()

    def add(raw: Any) -> None:
        if raw is None:
            return
        if isinstance(raw, dict):
            if raw.get("raw") or raw.get("city") or raw.get("remote"):
                key = repr(sorted((k, str(v)) for k, v in raw.items() if v is not None))
                if key in seen:
                    return
                seen.add(key)
                item = dict(raw)
                if "bucket" not in item:
                    blob = " ".join(str(item.get(k) or "") for k in ("raw", "city", "region"))
                    if item.get("remote") and not _city_bucket(blob):
                        item["bucket"] = "remote"
                    else:
                        item["bucket"] = _city_bucket(blob) or item.get("bucket") or "other"
                parsed.append(item)
                return
            raw = raw.get("name") or raw.get("location") or raw.get("label") or ""
        text = collapse_ws(str(raw))
        if not text:
            return
        for part in _split_raw(text):
            item = parse_one(part)
            key = f"{item.get('city')}|{item.get('bucket')}|{item.get('remote')}|{item.get('raw')}"
            if key in seen:
                continue
            seen.add(key)
            parsed.append(item)

    if isinstance(raw_list, list) and raw_list:
        for item in raw_list:
            add(item)
    add(job.get("location"))
    return parsed


def location_buckets_for(job: dict[str, Any]) -> list[str]:
    buckets: list[str] = []
    for loc in parse_locations(job):
        b = loc.get("bucket") or "other"
        if b not in buckets:
            buckets.append(b)
    if not buckets:
        buckets = ["other"]
    return buckets


def primary_location_bucket(job: dict[str, Any]) -> str:
    buckets = location_buckets_for(job)
    for preferred in ("nyc", "sf", "remote", "other"):
        if preferred in buckets:
            return preferred
    return buckets[0]


def location_blob(job: dict[str, Any]) -> str:
    parts = []
    if job.get("location"):
        parts.append(str(job["location"]))
    for loc in job.get("locations") or []:
        if isinstance(loc, str):
            parts.append(loc)
        elif isinstance(loc, dict):
            parts.append(str(loc.get("raw") or loc.get("city") or loc.get("name") or ""))
    return " ".join(parts).lower()


def city_matches(job: dict[str, Any], places: list[str] | None) -> bool:
    if not places:
        return False
    parsed = parse_locations(job)
    blob = location_blob(job)
    for place in places:
        n = _norm_place(place)
        if not n:
            continue
        if n in blob or _city_bucket(place) in location_buckets_for(job):
            return True
        for loc in parsed:
            city = _norm_place(str(loc.get("city") or ""))
            raw = _norm_place(str(loc.get("raw") or ""))
            if n and (n == city or n in city or n in raw or city in n):
                return True
    return False
