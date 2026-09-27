#!/usr/bin/env python3
"""Deterministic title/department → category + track. LLM only for needsLlm."""

from __future__ import annotations

import sys
from pathlib import Path


def _lib() -> Path:
    here = Path(__file__).resolve()
    for parent in here.parents:
        cand = parent / "lib"
        if (cand / "network_jobs").is_dir():
            return cand
    raise SystemExit("cannot find network-jobs lib/")


sys.path.insert(0, str(_lib()))
from network_jobs.cli import main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main(["classify", *sys.argv[1:]]))
