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
from .prefs import load_resume_keywords, match_listings, name_tokens
from .rank import DEFAULT_K, posting_age_days, rank_corpus


def _load_json(path: Path, default: Any) -> Any:
    if not path.is_file():
        return default
    return json.loads(path.read_text())


def _dump(payload: Any, verbose: bool) -> None:
    if verbose:
        print(json.dumps(payload, indent=2, ensure_ascii=False))
    else:
        print(json.dumps(payload, ensure_ascii=False))


def _do_match_prefs(
    triage_dir: Path,
    listings: list[dict[str, Any]],
    prefs: dict[str, Any],
    resume_text: str,
    exclude: set[str],
    company: str,
    verbose: bool,
) -> dict[str, Any]:
    result = match_listings(
        listings,
        prefs,
        resume_keywords=load_resume_keywords(resume_text, exclude=exclude) if resume_text else None,
        company=company or None,
    )
    out_dir = triage_dir / "index"
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
    upsert_inventory(triage_dir / "INVENTORY.md", summary)
    return result


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
    profile = _load_json(data / "profile.json", {})
    exclude = name_tokens(profile) if isinstance(profile, dict) else set()
    company = args.company or ""
    result = _do_match_prefs(triage, listings, prefs, resume_text, exclude, company, args.verbose)
    matches_path = triage / "index" / "matches.json"
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
        include_stale=getattr(args, "include_stale", False),
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
        "staleHidden": result.get("staleHidden", 0),
        "out": str(dest),
    }
    if args.verbose:
        quiet["shards"] = result.get("shards")
    _dump(quiet, args.verbose)
    return 0


def _fmt_salary(salary: Any) -> str:
    if not isinstance(salary, dict):
        return ""
    lo, hi = salary.get("min"), salary.get("max")
    if lo is None and hi is None:
        return ""

    def fmt(v: Any) -> str:
        if not isinstance(v, (int, float)):
            return "?"
        return f"${v / 1000:.0f}k" if v >= 1000 else f"${v:.0f}"

    if isinstance(lo, (int, float)) and isinstance(hi, (int, float)) and lo != hi:
        return f"{fmt(lo)}–{fmt(hi)}"
    return fmt(hi if hi is not None else lo)


def _fmt_age_days(age: int | None) -> str:
    if age is None:
        return ""
    if age <= 0:
        return "today"
    if age == 1:
        return "1d ago"
    return f"{age}d ago"


def cmd_search(args: argparse.Namespace) -> int:
    from datetime import date as _date

    result = rank_corpus(
        data_dir=args.data,
        k=args.k,
        query=args.query or None,
        include_stale=getattr(args, "include_stale", False),
    )
    if getattr(args, "json", False):
        _dump(result, args.verbose)
        return 0
    # Keep ranked.json fresh so follow-on steps (rank-intros) can use it.
    data = data_home(args.data)
    search_dir = data / "search"
    search_dir.mkdir(parents=True, exist_ok=True)
    (search_dir / "ranked.json").write_text(
        json.dumps(result, indent=2, ensure_ascii=False) + "\n"
    )
    print(result["showing"] + " match prefs" + (f" for {args.query!r}" if args.query else ""))
    if result.get("staleHidden"):
        print(f"({result['staleHidden']} stale postings hidden — re-run with --include-stale)")
    today = _date.today()
    for job in result["jobs"]:
        bits = [str(job.get("title") or "untitled"), str(job.get("company") or "")]
        salary = _fmt_salary(job.get("salary"))
        if salary:
            bits.append(salary)
        age = _fmt_age_days(posting_age_days(job.get("postedAt"), today))
        if age:
            bits.append(age)
        if job.get("stale"):
            bits.append("STALE")
        print("• " + " — ".join(bits))
        url = job.get("url") or job.get("jdUrl") or ""
        if url:
            print(f"  {url}")
    return 0


def cmd_companies(args: argparse.Namespace) -> int:
    from datetime import date as _date

    data = data_home(args.data)
    companies = _load_json(data / "companies" / "companies.json", [])
    if not isinstance(companies, list):
        companies = []
    rows = [c for c in companies if isinstance(c, dict)]
    sort = getattr(args, "sort", "connections")
    if sort == "name":
        rows.sort(key=lambda c: str(c.get("name") or "").lower())
    elif sort == "crawl":
        rows.sort(key=lambda c: str(c.get("lastCrawl") or ""))
    else:
        rows.sort(
            key=lambda c: (-int(c.get("connectionCount") or 0), str(c.get("name") or "").lower())
        )
    if getattr(args, "json", False):
        _dump(rows, args.verbose)
        return 0
    today = _date.today()
    print(f"{len(rows)} companies")
    for c in rows:
        name = str(c.get("name") or c.get("slug") or "?")
        conn = c.get("connectionCount")
        crawl = str(c.get("lastCrawl") or "never")
        age = _fmt_age_days(posting_age_days(c.get("lastCrawl"), today))
        digest = str(c.get("listingSetHash") or "")[:8] or "—"
        jobs_url = "jobsUrl" if c.get("jobsUrl") else "no-url"
        line = f"• {name} — conn={conn} — crawl={crawl}"
        if age:
            line += f" ({age})"
        print(line + f" — hash={digest} — {jobs_url}")
    return 0


def _do_refresh(
    data_dir: str | Path | None,
    company: str = "",
    limit: int = 5,
    max_pages: int = DEFAULT_MAX_PAGES,
    max_listings: int = DEFAULT_MAX_LISTINGS,
    fetch: Any = None,
    today: Any = None,
) -> list[dict[str, Any]]:
    """Re-crawl stored listings-JSON endpoints (oldest first), stage new matches.

    Fully deterministic: no model in the loop. Only companies whose row carries
    a jobsUrl (stamped by crawl-state --stamp --source-url) are eligible.
    """
    from datetime import date as _date
    from .text import slugify

    data = data_home(data_dir)
    today_s = str(today)[:10] if today else _date.today().isoformat()
    companies_path = data / "companies" / "companies.json"
    companies = _load_json(companies_path, [])
    if not isinstance(companies, list):
        companies = []
    prefs = _load_json(data / "preferences.json", {})
    if not isinstance(prefs, dict):
        prefs = {}
    resume_text = ""
    resume_path = data / "resume" / "text.md"
    if resume_path.is_file():
        resume_text = resume_path.read_text()
    profile = _load_json(data / "profile.json", {})
    exclude = name_tokens(profile) if isinstance(profile, dict) else set()

    targets = [c for c in companies if isinstance(c, dict) and c.get("jobsUrl")]
    if company:
        want = slugify(company)
        targets = [
            c for c in targets
            if slugify(str(c.get("name") or "")) == want or str(c.get("slug") or "") == want
        ]
    targets.sort(key=lambda c: str(c.get("lastCrawl") or ""))
    targets = targets[: max(1, int(limit or 5))]

    results: list[dict[str, Any]] = []
    for row in targets:
        name = str(row.get("name") or row.get("slug") or "?")
        slug = str(row.get("slug") or slugify(name))
        url = str(row.get("jobsUrl") or "")
        triage = data / "triage" / f"careers-{slug}-{today_s}"
        try:
            pres = paginate(
                url,
                max_pages=max_pages,
                max_listings=max_listings,
                fetch=fetch,
                source_url=url,
                company=name,
            )
            write_pagination(triage, pres, company=name)
            listings = pres.get("listings") or []
            listings_path = triage / "index" / "listings.json"
            status = _do_crawl_state(
                data, triage, listings_path, companies_path,
                slug, name, False, None, False,
            )
            if status.get("unchanged"):
                _do_crawl_state(
                    data, triage, listings_path, companies_path,
                    slug, name, True, url, False,
                )
                results.append({
                    "company": name, "slug": slug, "status": "unchanged",
                    "listings": len(listings),
                })
            else:
                mres = _do_match_prefs(triage, listings, prefs, resume_text, exclude, name, False)
                _do_crawl_state(
                    data, triage, listings_path, companies_path,
                    slug, name, True, url, False,
                )
                results.append({
                    "company": name, "slug": slug, "status": "changed",
                    "listings": len(listings), "matches": mres["nMatches"],
                    "triage": str(triage),
                })
        except Exception as exc:  # noqa: BLE001 — one bad board must not kill the run
            results.append({
                "company": name, "slug": slug, "status": "error",
                "error": f"{type(exc).__name__}: {exc}",
            })
    return results


def cmd_refresh(args: argparse.Namespace) -> int:
    if args.company:
        pass  # filtered inside _do_refresh; unknown names just yield no targets
    results = _do_refresh(
        args.data,
        company=args.company or "",
        limit=args.limit,
        max_pages=args.max_pages,
        max_listings=args.max_listings,
    )
    if getattr(args, "json", False):
        _dump({"refreshed": len(results), "results": results}, args.verbose)
        return 0
    if not results:
        print("No companies with a stored jobsUrl to refresh.")
        print("Re-run careers-discover (it stamps jobsUrl via crawl-state --stamp --source-url),")
        print("or stamp one manually: crawl-state --company NAME --stamp --source-url URL --listings …")
        return 0
    for r in results:
        status = r["status"]
        if status == "unchanged":
            print(f"• {r['company']}: unchanged ({r['listings']} listings)")
        elif status == "changed":
            print(f"• {r['company']}: {r['matches']} of {r['listings']} match prefs → staged at {r['triage']}")
        else:
            print(f"• {r['company']}: ERROR {r.get('error')}")
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


def _do_crawl_state(
    data: Path,
    triage: Path | None,
    listings_path: Path | None,
    companies_path: Path,
    slug_or_name: str,
    company_name: str | None,
    stamp: bool,
    source_url: str | None,
    verbose: bool,
) -> dict[str, Any]:
    from .crawl import crawl_status, stamp_company_crawl
    from .inventory import upsert_inventory, write_summary_json

    listings = _load_json(listings_path, []) if listings_path else []
    if not isinstance(listings, list):
        listings = []
    companies = _load_json(companies_path, [])
    if not isinstance(companies, list):
        companies = []
    pagination = {}
    if triage and (triage / "index" / "pagination.json").is_file():
        pagination = _load_json(triage / "index" / "pagination.json", {}) or {}
    if stamp:
        status = stamp_company_crawl(
            companies_path,
            slug_or_name,
            listings,
            pagination=pagination if isinstance(pagination, dict) else None,
            company_name=company_name,
            source_url=source_url,
        )
    else:
        status = crawl_status(
            companies,
            slug_or_name,
            listings,
            company_name=company_name,
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
    return status


def cmd_crawl_state(args: argparse.Namespace) -> int:
    data = data_home(args.data)
    triage = Path(args.triage_dir).expanduser().resolve() if args.triage_dir else None
    listings_path = Path(args.listings) if args.listings else (
        (triage / "index" / "listings.json") if triage else None
    )
    if listings_path is None:
        print("crawl-state requires --listings or --triage-dir", file=sys.stderr)
        return 1
    companies_path = Path(args.companies) if args.companies else data / "companies" / "companies.json"
    status = _do_crawl_state(
        data,
        triage,
        listings_path,
        companies_path,
        args.company or args.slug,
        args.company or None,
        args.stamp,
        getattr(args, "source_url", None),
        args.verbose,
    )
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
    r.add_argument("--include-stale", action="store_true",
                   help="include stale postings (hidden by default)")
    r.set_defaults(func=cmd_rank)

    s = sub.add_parser("search", help="rank the corpus and print a human-readable list")
    s.add_argument("--query", default="")
    s.add_argument("-k", type=int, default=DEFAULT_K)
    s.add_argument("--data")
    s.add_argument("--include-stale", action="store_true",
                   help="include stale postings (hidden by default)")
    s.add_argument("--json", action="store_true",
                   help="print the ranked payload instead of a list")
    s.set_defaults(func=cmd_search)

    co = sub.add_parser("companies", help="list the company graph")
    co.add_argument("--data")
    co.add_argument("--json", action="store_true", help="print companies.json rows")
    co.add_argument("--sort", default="connections",
                    choices=["connections", "name", "crawl"])
    co.set_defaults(func=cmd_companies)

    rf = sub.add_parser("refresh", help="re-crawl known listings endpoints, stage new matches")
    rf.add_argument("--data")
    rf.add_argument("--company", default="", help="only refresh this company (name or slug)")
    rf.add_argument("--limit", type=int, default=5, help="max companies per run (oldest crawl first)")
    rf.add_argument("--max-pages", type=int, default=DEFAULT_MAX_PAGES)
    rf.add_argument("--max-listings", type=int, default=DEFAULT_MAX_LISTINGS)
    rf.add_argument("--json", action="store_true", help="print a machine-readable summary")
    rf.set_defaults(func=cmd_refresh)

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
    cr.add_argument("--source-url", default="",
                    help="listings JSON endpoint; stored as jobsUrl when stamping (used by refresh)")
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
