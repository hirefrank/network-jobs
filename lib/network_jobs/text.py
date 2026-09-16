"""Normalization helpers shared by fingerprinting, matching, and import."""

from __future__ import annotations

import re

SUFFIX_RE = re.compile(
    r"\b(inc|incorporated|corp|corporation|llc|ltd|limited|llp|lp|plc|co|company|"
    r"group|holdings|worldwide|international|global|technologies|technology|"
    r"solutions|services)\b",
    re.I,
)
PUNCT_RE = re.compile(r"[.,/#!$%^&*;:{}=\-_`~()•\"']")
WS_RE = re.compile(r"\s+")

STOPWORDS = {
    "a", "an", "the", "and", "or", "of", "to", "for", "in", "on", "at", "by",
    "with", "from", "as", "is", "are", "be", "this", "that", "it", "we", "our",
    "you", "your", "their", "they", "i", "me", "my", "was", "were", "been",
    "have", "has", "had", "will", "can", "into", "over", "than", "then",
}


def collapse_ws(value: str) -> str:
    return WS_RE.sub(" ", (value or "").strip())


def basic_normalize(value: str) -> str:
    s = collapse_ws(value).lower()
    s = PUNCT_RE.sub(" ", s)
    s = SUFFIX_RE.sub(" ", s)
    return collapse_ws(s)


def normalize_company(name: str) -> str:
    return basic_normalize(name)


def slugify(normalized: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", (normalized or "").lower()).strip("-")
    return s or "unknown"


def normalize_title(title: str) -> str:
    s = collapse_ws(title).lower()
    s = s.replace("&", " and ")
    s = PUNCT_RE.sub(" ", s)
    s = re.sub(r"\b(sr|snr)\b", "senior", s)
    s = re.sub(r"\bjr\b", "junior", s)
    s = collapse_ws(s)
    return s


def tokenize(value: str) -> list[str]:
    return [t for t in re.findall(r"[a-z0-9][a-z0-9+\-/#]{1,}", (value or "").lower()) if t not in STOPWORDS]


def former_employer_match(company: str, former_employers: list[str] | None) -> bool:
    if not former_employers:
        return False
    needle = normalize_company(company)
    if not needle:
        return False
    for name in former_employers:
        other = normalize_company(name)
        if other and (needle == other or needle in other or other in needle):
            return True
    return False
