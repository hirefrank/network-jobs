"""CLI entry points used by skill helpers. Quiet JSON on stdout; -v for detail."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from .classify import classify_listings
from .corpus import rebuild
from .inventory import upsert_inventory, write_summary_json
from .pagination import DEFAULT_MAX_LISTINGS, DEFAULT_MAX_PAGES, paginate, write_pagination
from .paths import data_home
from .prefs import load_resume_keywords, match_listings
from .rank import DEFAULT_K, rank_corpus


def _load_json(path: Path, default: Any) -> Any:
    if not path.is_file():
        return default
    return json.loads(path.read_text())


def _dump(payload: Any, verbose: bool) -> None:
    if verbose:
        print(json.dumps(payload, indent=2, ensure_ascii=False))
    else:
        print(json.dumps(payload, ensure_ascii=False))


def cmd_match_prefs(args: argparse.Namespace) -> int:
    triage = Path(args.triage_dir).expanduser().resolve()
    listings_path = Path(args.listings) if args.listings else triage / "index" / "listings.json"
    listings = _load_json(listings_path, [])
    if not isinstance(listings, list):
        print("listings.json must be a JSON array", file=sys.stderr)
        return 1
    data = data_home(args.data)
    prefs_path = Path(args.prefs) if args.prefs else data / "preferences.json"
    prefs = _load_json(prefs_path, {})
    if not isinstance(prefs, dict):
        prefs = {}
    resume_text = ""
    resume_path = Path(args.resume) if args.resume else data / "resume" / "text.md"
    if resume_path.is_file():
        resume_text = resume_path.read_text()
    company = args.company or ""
    result = match_listings(
        listings,
        prefs,
        resume_keywords=load_resume_keywords(resume_text) if resume_text else None,
        company=company or None,
    )
    out_dir = triage / "index"
    out_dir.mkdir(parents=True, exist_ok=True)
    matches_path = out_dir / "matches.json"
    payload = {
        "nListings": result["nListings"],
        "nMatches": result["nMatches"],
        "showing": result["showing"],
        "departments": result["departments"],
        "ingestDefault": "matches",
        "jobs": result["jobs"],
    }
    matches_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n")
    summary = {
        "company": company,
        "nListings": result["nListings"],
        "nMatches": result["nMatches"],
        "departments": result["departments"],
        "ingestDefault": "matches",
    }
    existing = _load_json(out_dir / "summary.json", {})
    if isinstance(existing, dict):
        summary = {**existing, **summary}
    write_summary_json(out_dir, summary)
    upsert_inventory(triage / "INVENTORY.md", summary)
    quiet = {
        "matches": result["nMatches"],
        "listings": result["nListings"],
        "showing": result["showing"],
        "out": str(matches_path),
        "ingestDefault": "matches",
    }
    if args.verbose:
        quiet["departments"] = result["departments"]
    _dump(quiet, args.verbose)
    return 0


def cmd_rank(args: argparse.Namespace) -> int:
    result = rank_corpus(
        data_dir=args.data,
        k=args.k,
        query=args.query,
    )
    data = data_home(args.data)
    search_dir = data / "search"
    search_dir.mkdir(parents=True, exist_ok=True)
    dest = Path(args.out) if args.out else search_dir / "ranked.json"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n")
    quiet = {
        "k": result["k"],
        "n": result["n"],
        "showing": result["showing"],
        "out": str(dest),
    }
    if args.verbose:
        quiet["shards"] = result.get("shards")
    _dump(quiet, args.verbose)
    return 0


def cmd_paginate(args: argparse.Namespace) -> int:
    payload = None
    url = args.url
    if args.input:
        payload = _load_json(Path(args.input), None)
        url = url or ""
    if not url and payload is None:
        print("paginate requires --url or --input", file=sys.stderr)
        return 1
    result = paginate(
        url or None,
        payload=payload if not url else None,
        max_pages=args.max_pages,
        max_listings=args.max_listings,
        source_url=url or str(args.input or ""),
        company=args.company or "",
    )
    quiet = write_pagination(Path(args.triage_dir), result, company=args.company or "")
    _dump(quiet, args.verbose)
    return 0


def cmd_rebuild(args: argparse.Namespace) -> int:
    data = data_home(args.data)
    complete = bool(args.pagination_complete)
    if args.pagination_incomplete:
        complete = False
    summary = rebuild(
        Path(args.batch),
        data / "corpus",
        expire_company=args.expire_company or None,
        pagination_complete=complete,
    )
    _dump(summary if args.verbose else {
        "totalJobs": summary["totalJobs"],
        "incoming": summary["incoming"],
        "closedJobs": summary.get("closedJobs", 0),
        "expired": summary.get("expired", False),
        "paginationComplete": summary.get("paginationComplete", False),
    }, args.verbose)
    return 0


def cmd_classify(args: argparse.Namespace) -> int:
    listings = _load_json(Path(args.input), [])
    if not isinstance(listings, list):
        print("input must be a JSON array", file=sys.stderr)
        return 1
    result = classify_listings(listings, company=args.company or None)
    dest = Path(args.out) if args.out else Path(args.input)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(result["jobs"], indent=2, ensure_ascii=False) + "\n")
    quiet = {
        "n": result["n"],
        "ambiguous": result["ambiguous"],
        "out": str(dest),
    }
    if args.verbose:
        quiet["needsLlm"] = result["needsLlm"]
    _dump(quiet, args.verbose)
    return 0


def cmd_crawl_state(args: argparse.Namespace) -> int:
    from .crawl import crawl_status, stamp_company_crawl
    from .inventory import upsert_inventory, write_summary_json

    data = data_home(args.data)
    triage = Path(args.triage_dir).expanduser().resolve() if args.triage_dir else None
    listings_path = Path(args.listings) if args.listings else (
        (triage / "index" / "listings.json") if triage else None
    )
    if listings_path is None:
        print("crawl-state requires --listings or --triage-dir", file=sys.stderr)
        return 1
    listings = _load_json(listings_path, [])
    if not isinstance(listings, list):
        listings = []
    companies_path = Path(args.companies) if args.companies else data / "companies" / "companies.json"
    companies = _load_json(companies_path, [])
    if not isinstance(companies, list):
        companies = []
    pagination = {}
    if triage and (triage / "index" / "pagination.json").is_file():
        pagination = _load_json(triage / "index" / "pagination.json", {}) or {}
    if args.stamp:
        status = stamp_company_crawl(
            companies_path,
            args.company or args.slug,
            listings,
            pagination=pagination if isinstance(pagination, dict) else None,
            company_name=args.company or None,
        )
    else:
        status = crawl_status(
            companies,
            args.company or args.slug,
            listings,
            company_name=args.company or None,
        )
    if triage:
        summary = _load_json(triage / "index" / "summary.json", {})
        if not isinstance(summary, dict):
            summary = {}
        summary["crawl"] = {
            "unchanged": status.get("unchanged"),
            "listingSetHash": status.get("listingSetHash"),
            "lastCrawl": status.get("lastCrawl"),
        }
        write_summary_json(triage / "index", summary)
        upsert_inventory(triage / "INVENTORY.md", summary)
    quiet = {
        "unchanged": status.get("unchanged"),
        "listingSetHash": status.get("listingSetHash"),
        "lastCrawl": status.get("lastCrawl"),
        "skipIngest": bool(status.get("unchanged")),
    }
    if args.verbose:
        quiet.update(status)
    _dump(quiet, args.verbose)
    return 0


def cmd_rank_intros(args: argparse.Namespace) -> int:
    from .intros import rank_intros
    from .paths import data_home as dh

    data = dh(args.data)
    jobs_path = Path(args.jobs) if args.jobs else data / "search" / "ranked.json"
    payload = _load_json(jobs_path, {})
    if isinstance(payload, dict):
        jobs = payload.get("jobs") or []
    elif isinstance(payload, list):
        jobs = payload
    else:
        jobs = []
    connections = _load_json(
        Path(args.connections) if args.connections else data / "connections" / "connections.json",
        [],
    )
    if not isinstance(connections, list):
        connections = []
    result = rank_intros(jobs, connections, k_roles=args.k_roles, k_forwarders=args.k_forwarders)
    dest = Path(args.out) if args.out else data / "search" / "intros.json"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n")
    quiet = {
        "roles": result["kRoles"],
        "forwarders": args.k_forwarders,
        "fetchJdUrls": result["fetchJdUrls"],
        "out": str(dest),
        "showing": result["showing"],
    }
    _dump(quiet, args.verbose)
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="network-jobs-helper", add_help=True)
    p.add_argument("-v", "--verbose", action="store_true", help="print extra fields")
    sub = p.add_subparsers(dest="cmd", required=True)

    m = sub.add_parser("match-prefs", help="score triage listings against preferences.json")
    m.add_argument("--triage-dir", required=True)
    m.add_argument("--listings")
    m.add_argument("--prefs")
    m.add_argument("--resume")
    m.add_argument("--data")
    m.add_argument("--company", default="")
    m.set_defaults(func=cmd_match_prefs)

    r = sub.add_parser("rank", help="rank corpus shards to search/ranked.json")
    r.add_argument("--data")
    r.add_argument("-k", type=int, default=DEFAULT_K)
    r.add_argument("--query", default="")
    r.add_argument("--out")
    r.set_defaults(func=cmd_rank)

    g = sub.add_parser("paginate", help="follow page/cursor/offset into listings.json")
    g.add_argument("--url")
    g.add_argument("--input", help="local JSON file instead of fetching")
    g.add_argument("--triage-dir", required=True)
    g.add_argument("--company", default="")
    g.add_argument("--max-pages", type=int, default=DEFAULT_MAX_PAGES)
    g.add_argument("--max-listings", type=int, default=DEFAULT_MAX_LISTINGS)
    g.set_defaults(func=cmd_paginate)

    b = sub.add_parser("rebuild", help="merge batch into corpus by fingerprint")
    b.add_argument("batch")
    b.add_argument("--data")
    b.add_argument("--expire-company", default="")
    b.add_argument("--pagination-complete", action="store_true")
    b.add_argument("--pagination-incomplete", action="store_true")
    b.set_defaults(func=cmd_rebuild)

    c = sub.add_parser("classify", help="title/department → category, track, seniority")
    c.add_argument("--input", required=True)
    c.add_argument("--out")
    c.add_argument("--company", default="")
    c.set_defaults(func=cmd_classify)

    cr = sub.add_parser("crawl-state", help="listing-set hash vs lastCrawl; skip unchanged boards")
    cr.add_argument("--triage-dir")
    cr.add_argument("--listings")
    cr.add_argument("--companies")
    cr.add_argument("--data")
    cr.add_argument("--company", default="")
    cr.add_argument("--slug", default="")
    cr.add_argument("--stamp", action="store_true", help="write lastCrawl + hash onto companies.json")
    cr.set_defaults(func=cmd_crawl_state)

    ri = sub.add_parser("rank-intros", help="1–2 roles + 1–2 forwarders from full connections.json")
    ri.add_argument("--data")
    ri.add_argument("--jobs")
    ri.add_argument("--connections")
    ri.add_argument("--out")
    ri.add_argument("--k-roles", type=int, default=2)
    ri.add_argument("--k-forwarders", type=int, default=2)
    ri.set_defaults(func=cmd_rank_intros)

    return p


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args) or 0)


if __name__ == "__main__":
    raise SystemExit(main())
