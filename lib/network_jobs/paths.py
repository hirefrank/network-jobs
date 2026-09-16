"""Resolve suite root and data home without requiring a shell source."""

from __future__ import annotations

import os
import sys
from pathlib import Path


def data_home(explicit: str | Path | None = None) -> Path:
    if explicit:
        return Path(explicit).expanduser().resolve()
    return Path(os.environ.get("NETWORK_JOBS_HOME", Path.home() / ".network-jobs")).expanduser().resolve()


def suite_root(start: Path | None = None) -> Path:
    env = os.environ.get("NETWORK_JOBS_SUITE")
    if env:
        root = Path(env).expanduser().resolve()
        if (root / "lib" / "network_jobs").is_dir():
            return root

    here = (start or Path(__file__)).resolve()
    for parent in [here, *here.parents]:
        if (parent / "lib" / "network_jobs").is_dir() and (parent / "SCHEMA.md").is_file():
            return parent

    marker = data_home() / "suite-root"
    if marker.is_file():
        root = Path(marker.read_text().strip()).expanduser()
        if (root / "lib" / "network_jobs").is_dir():
            return root.resolve()

    raise FileNotFoundError(
        "Cannot find the network-jobs suite root. Set NETWORK_JOBS_SUITE or run setup."
    )


def ensure_lib_path() -> Path:
    lib = suite_root() / "lib"
    lib_s = str(lib)
    if lib_s not in sys.path:
        sys.path.insert(0, lib_s)
    return lib
