"""Incremental crawl budget: listing-set hash + lastCrawl on the company graph."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .fingerprint import listing_set_hash
from .text import slugify, normalize_company

MAX_API_PAGES = 15
MAX_BROWSER_PAGES = 5
MAX_LISTINGS = 2000


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_companies(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    data = json.loads(path.read_text())
    return data if isinstance(data, list) else []


def find_company(companies: list[dict[str, Any]], slug_or_name: str) -> dict[str, Any] | None:
    want = slugify(normalize_company(slug_or_name) or slug_or_name)
    for row in companies:
        slug = str(row.get("slug") or slugify(str(row.get("normalized") or row.get("name") or "")))
        if slug == want or slugify(str(row.get("name") or "")) == want:
            return row
    return None


def crawl_status(
    companies: list[dict[str, Any]],
    slug_or_name: str,
    listings: list[dict[str, Any]],
    company_name: str | None = None,
) -> dict[str, Any]:
    digest = listing_set_hash(listings, company=company_name or slug_or_name)
    row = find_company(companies, slug_or_name)
    prev = (row or {}).get("listingSetHash") or ""
    unchanged = bool(prev) and prev == digest
    return {
        "unchanged": unchanged,
        "listingSetHash": digest,
        "previousHash": prev,
        "lastCrawl": (row or {}).get("lastCrawl"),
        "slug": (row or {}).get("slug") or slugify(slug_or_name),
        "maxApiPages": MAX_API_PAGES,
        "maxBrowserPages": MAX_BROWSER_PAGES,
        "maxListings": MAX_LISTINGS,
    }


def stamp_company_crawl(
    companies_path: Path,
    slug_or_name: str,
    listings: list[dict[str, Any]],
    pagination: dict[str, Any] | None = None,
    company_name: str | None = None,
    source_url: str | None = None,
) -> dict[str, Any]:
    companies = _load_companies(companies_path)
    status = crawl_status(companies, slug_or_name, listings, company_name=company_name)
    row = find_company(companies, slug_or_name)
    if row is None:
        row = {
            "name": company_name or slug_or_name,
            "normalized": normalize_company(company_name or slug_or_name),
            "slug": slugify(normalize_company(company_name or slug_or_name) or slug_or_name),
            "domain": "",
            "connectionCount": 0,
            "people": [],
        }
        companies.append(row)
    row["lastCrawl"] = _now()
    row["listingSetHash"] = status["listingSetHash"]
    if source_url:
        # The listings JSON endpoint this crawl paginated; refresh uses it to
        # re-crawl deterministically without a model in the loop.
        row["jobsUrl"] = source_url
    if pagination:
        row["lastPagination"] = {
            "pages": pagination.get("pages"),
            "complete": pagination.get("complete"),
            "truncated": pagination.get("truncated"),
        }
    companies_path.parent.mkdir(parents=True, exist_ok=True)
    companies_path.write_text(json.dumps(companies, indent=2, ensure_ascii=False) + "\n")
    status["lastCrawl"] = row["lastCrawl"]
    status["stamped"] = True
    return status
