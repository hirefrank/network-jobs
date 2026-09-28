"""Build a publishable, privacy-safe network pack from a LinkedIn export.

A pack is a company-aggregated map of someone's professional network:
company names, connection counts, and title keywords — no names, emails,
profile URLs, or dates. The owner can publish it (e.g. as a release asset)
so others can discover *where* they have connections without ever seeing
*who* those connections are. Intro requests still go through the owner.

Privacy rules (deliberate, not incidental):
- Names, emails, URLs, and connected-on dates are dropped at parse time —
  they never reach the aggregation step.
- Title keywords are published only for companies with >= TITLE_MIN_COUNT
  connections (default 3): a lone "CEO" at a 2-person startup is identifying.
- The same company ignore lists as the LinkedIn import apply, so noise like
  "Self-employed" never ships.
"""

from __future__ import annotations

import csv
import io
import json
import zipfile
from collections import Counter
from datetime import date
from pathlib import Path
from typing import Any

from .text import basic_normalize, normalize_title, slugify

TITLE_MIN_COUNT = 3
TOP_TITLES = 3


def _repo_assets() -> Path:
    return Path(__file__).resolve().parents[2] / "skills" / "network-jobs-import" / "assets"


def _load_json(path: Path, default: Any) -> Any:
    try:
        with path.open(encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return default


def _ignore_sets(assets: Path) -> tuple[set[str], set[str], dict[str, str]]:
    ignore_companies = {
        basic_normalize(x)
        for x in _load_json(assets / "companies-to-ignore.json", [])
        if isinstance(x, str)
    }
    ignore_words = {
        str(w).lower()
        for w in _load_json(assets / "company-words-to-ignore.json", [])
        if isinstance(w, str)
    }
    overrides = {
        basic_normalize(o["linkedinName"]): basic_normalize(o["matchTo"])
        for o in _load_json(assets / "company-overrides.json", [])
        if isinstance(o, dict) and "linkedinName" in o and "matchTo" in o
    }
    return ignore_companies, ignore_words, overrides


def _normalize_company(name: str, overrides: dict[str, str]) -> str:
    n = basic_normalize(name)
    return overrides.get(n, n)


def _should_ignore(normalized: str, ignore_companies: set[str], ignore_words: set[str]) -> bool:
    if not normalized:
        return True
    if normalized in ignore_companies:
        return True
    return any(w in normalized for w in ignore_words)


def _read_connections_csv(source: str | Path) -> list[dict[str, str]]:
    """Parse a LinkedIn Connections.csv or .zip export into raw rows.

    Only company + position are retained — every other column is dropped here,
    before aggregation, so PII cannot leak downstream.
    """
    src = Path(source)
    if not src.is_file():
        raise FileNotFoundError(f"not found: {src}")

    if src.suffix.lower() == ".zip":
        with zipfile.ZipFile(src) as zf:
            names = [n for n in zf.namelist() if n.lower().endswith("connections.csv")]
            if not names:
                raise ValueError("Connections.csv not found inside ZIP")
            text = zf.read(names[0]).decode("utf-8-sig", errors="replace")
    else:
        text = src.read_text(encoding="utf-8-sig", errors="replace")

    # LinkedIn may prepend notes before the header row.
    lines = text.splitlines()
    header_idx = next(
        (i for i, line in enumerate(lines)
         if "first name" in line.lower() and "company" in line.lower()),
        None,
    )
    if header_idx is None:
        raise ValueError("could not find Connections CSV header (First Name + Company)")

    reader = csv.DictReader(lines[header_idx:])
    rows: list[dict[str, str]] = []
    for row in reader:
        lowered = {(k or "").lower().strip(): (v or "").strip() for k, v in row.items()}

        def get(*keys: str) -> str:
            for key in keys:
                for lk, v in lowered.items():
                    if key == lk or key in lk:
                        return v
            return ""

        company = get("company")
        if not company:
            continue
        rows.append({"company": company, "position": get("position")})
    return rows


def build_pack(
    source: str | Path,
    label: str = "",
    min_count: int = 1,
    title_min_count: int = TITLE_MIN_COUNT,
    generated_on: str | None = None,
) -> dict[str, Any]:
    """Aggregate a LinkedIn export into a publishable network pack dict."""
    assets = _repo_assets()
    ignore_companies, ignore_words, overrides = _ignore_sets(assets)

    agg: dict[str, dict[str, Any]] = {}
    for row in _read_connections_csv(source):
        norm = _normalize_company(row["company"], overrides)
        if _should_ignore(norm, ignore_companies, ignore_words):
            continue
        entry = agg.get(norm)
        if entry is None:
            entry = agg[norm] = {
                "name": row["company"],
                "name_counts": Counter(),
                "connectionCount": 0,
                "titles": Counter(),
            }
        entry["name_counts"][row["company"]] += 1
        entry["connectionCount"] += 1
        title = normalize_title(row["position"])
        if title:
            entry["titles"][title] += 1

    companies = []
    for norm, entry in agg.items():
        if entry["connectionCount"] < min_count:
            continue
        # Display name = the most common raw spelling the owner used.
        name = entry["name_counts"].most_common(1)[0][0]
        company: dict[str, Any] = {
            "name": name,
            "normalized": norm,
            "slug": slugify(norm),
            "connectionCount": entry["connectionCount"],
        }
        if entry["connectionCount"] >= title_min_count:
            company["topTitles"] = [t for t, _ in entry["titles"].most_common(TOP_TITLES)]
        companies.append(company)
    companies.sort(key=lambda c: (-c["connectionCount"], c["name"].lower()))

    return {
        "pack": "network-jobs",
        "packVersion": 1,
        "label": label,
        "generatedAt": generated_on or date.today().isoformat(),
        "source": "LinkedIn connections export (company-aggregated; no personal data)",
        "totalConnections": sum(e["connectionCount"] for e in agg.values()),
        "companies": companies,
    }


def default_pack_path(label: str, generated_on: str | None = None) -> str:
    slug = slugify(basic_normalize(label)) if label else "network"
    day = generated_on or date.today().isoformat()
    return f"{slug}-network-pack-{day}.json"


def write_pack(pack: dict[str, Any], out_path: str | Path) -> Path:
    out = Path(out_path)
    out.write_text(json.dumps(pack, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return out
