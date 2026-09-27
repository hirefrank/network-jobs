"""Deterministic INVENTORY.md summary block (helpers, not the model)."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

MARKER_START = "<!-- nj-summary:start -->"
MARKER_END = "<!-- nj-summary:end -->"


def department_histogram_line(departments: dict[str, int], limit: int = 12) -> str:
    items = sorted(departments.items(), key=lambda kv: (-kv[1], kv[0]))[:limit]
    if not items:
        return "(none)"
    return ", ".join(f"{name} ({count})" for name, count in items)


def render_summary_block(summary: dict[str, Any]) -> str:
    listings = summary.get("nListings", summary.get("listings", 0))
    matches = summary.get("nMatches")
    pages = summary.get("pagination") or {}
    lines = [
        MARKER_START,
        f"- **Listings:** {listings}",
    ]
    if matches is not None:
        lines.append(f"- **Matches:** {matches} of {listings} match prefs")
    depts = summary.get("departments") or {}
    if depts:
        lines.append(f"- **Departments:** {department_histogram_line(depts)}")
    if pages:
        complete = "true" if pages.get("complete") else "false"
        truncated = "true" if pages.get("truncated") else "false"
        lines.append(
            f"- **Pagination:** pages={pages.get('pages', 0)}, complete={complete}, truncated={truncated}"
        )
        extra = pages.get("scheme")
        if extra:
            lines.append(f"- **Pagination scheme:** {extra}")
    crawl = summary.get("crawl") or {}
    if crawl:
        if crawl.get("unchanged"):
            lines.append("- **Crawl:** listing-set hash unchanged — skip refresh")
        elif crawl.get("listingSetHash"):
            lines.append(f"- **Crawl hash:** {crawl['listingSetHash']}")
    ingest = summary.get("ingestDefault") or "matches"
    lines.append(f"- **Ingest default:** {ingest} (say “ingest all” or a department to override)")
    lines.append(MARKER_END)
    return "\n".join(lines) + "\n"


def upsert_inventory(path: Path, summary: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    block = render_summary_block(summary)
    if path.is_file():
        text = path.read_text()
        if MARKER_START in text and MARKER_END in text:
            text = re.sub(
                re.escape(MARKER_START) + r".*?" + re.escape(MARKER_END),
                block.strip(),
                text,
                count=1,
                flags=re.S,
            )
        else:
            text = text.rstrip() + "\n\n## Pipeline summary\n\n" + block
        path.write_text(text if text.endswith("\n") else text + "\n")
    else:
        name = summary.get("company") or "company"
        path.write_text(f"# Careers triage — {name}\n\n{block}")


def write_summary_json(index_dir: Path, summary: dict[str, Any]) -> Path:
    index_dir.mkdir(parents=True, exist_ok=True)
    dest = index_dir / "summary.json"
    dest.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n")
    return dest
