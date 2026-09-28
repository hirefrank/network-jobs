"""Tolerant date parsing shared by ingest (postedAt normalization) and rank."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any
import re

_ISO_RE = re.compile(r"^(\d{4})-(\d{2})-(\d{2})")
_FMTS = ("%Y/%m/%d", "%m/%d/%Y", "%b %d, %Y", "%B %d, %Y")


def parse_date_flexible(raw: Any) -> date | None:
    """Best-effort anything → date. ATS formats vary wildly; None when unknown."""
    if not raw:
        return None
    if isinstance(raw, datetime):
        return raw.date()
    if isinstance(raw, date):
        return raw
    s = str(raw).strip()
    m = _ISO_RE.match(s)
    if m:
        try:
            return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        except ValueError:
            return None
    for fmt in _FMTS:
        try:
            return datetime.strptime(s[:24], fmt).date()
        except ValueError:
            continue
    return None


def normalize_date_iso(raw: Any) -> str | None:
    """Canonical YYYY-MM-DD when parseable, else None (caller keeps raw)."""
    d = parse_date_flexible(raw)
    return d.isoformat() if d else None
