"""CLI entry points used by skill helpers. Quiet JSON on stdout; -v for detail."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from .inventory import upsert_inventory, write_summary_json
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

    return p


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args) or 0)


if __name__ == "__main__":
    raise SystemExit(main())
