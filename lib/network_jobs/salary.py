"""Parse human salary strings into {min, max, currency, unit}.

ATS payloads carry salary as "$150k–$180k", "$150,000 - $180,000", "From
$120,000 a year", "£80k", etc. This normalizes to annual numbers when the
unit is annual (or unspecified); hourly rates are flagged, not annualized,
so prefs salaryMin never compares a barista wage against a tech salary.
"""

from __future__ import annotations

import re
from typing import Any

_CURRENCY = {"$": "USD", "€": "EUR", "£": "GBP", "¥": "JPY", "₹": "INR", "C$": "CAD", "A$": "AUD"}

_NUM_RE = re.compile(
    r"(?P<cur>[$€£¥₹]|C\$|A\$)?\s*(?P<num>\d[\d,]*\.?\d*)\s*(?P<suffix>[kKmM])?\b"
)
_HOURLY_RE = re.compile(r"/\s*(hour|hr\b)|per hour|an hour", re.I)
_RANGE_SEP_RE = re.compile(r"\s*(?:–|—|-|to|\.\.\.)\s*")


def _to_annual(num: float, suffix: str | None) -> float:
    if suffix and suffix.lower() == "k":
        return num * 1000
    if suffix and suffix.lower() == "m":
        return num * 1_000_000
    return num


def parse_salary(raw: Any) -> dict[str, Any] | None:
    """Parse a salary string (or pass through a numeric dict)."""
    if isinstance(raw, dict):
        lo, hi = raw.get("min"), raw.get("max")
        if isinstance(lo, (int, float)) or isinstance(hi, (int, float)):
            out = dict(raw)
            out.setdefault("currency", raw.get("currency") or "USD")
            return out
        return None
    if not isinstance(raw, str):
        return None
    s = raw.strip()
    if not s or len(s) > 120:
        return None

    hourly = bool(_HOURLY_RE.search(s))
    currency = "USD"
    # Check longer symbols first: "$" is a substring of "C$" and "A$".
    for sym, code in sorted(_CURRENCY.items(), key=lambda kv: -len(kv[0])):
        if sym in s:
            currency = code
            break

    hits = list(_NUM_RE.finditer(s))
    amounts = [a for a in hits if a.group("num")]
    if not amounts:
        return None

    def val(m: re.Match) -> float:
        return _to_annual(float(m.group("num").replace(",", "")), m.group("suffix"))

    # Range: first two amounts around a separator; single amount otherwise.
    parts = _RANGE_SEP_RE.split(s)
    if len(amounts) >= 2 and len(parts) >= 2:
        lo, hi = val(amounts[0]), val(amounts[1])
        if lo > hi:
            lo, hi = hi, lo
    else:
        lo = hi = val(amounts[0])
        lowered = s.lower()
        if re.search(r"\b(up to|upto|max)\b", lowered):
            lo, hi = 0, lo
        # "from $X" / "$X+" imply X is the floor; hi stays X (unknown ceiling).

    if lo <= 0 and hi <= 0:
        return None
    out: dict[str, Any] = {"min": round(lo, 2), "max": round(hi, 2), "currency": currency}
    if hourly:
        out["unit"] = "hourly"
    return out
