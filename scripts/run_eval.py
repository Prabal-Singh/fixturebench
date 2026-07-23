#!/usr/bin/env python3
"""Thin wrapper — prefer the ``fixturebench`` console script."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from fixturebench.cli import main

if __name__ == "__main__":
    # Map legacy flags onto the new subcommand CLI.
    argv = sys.argv[1:]
    if argv and argv[0] not in {"list", "run", "-h", "--help"}:
        if "--list" in argv:
            argv = ["list", *[a for a in argv if a != "--list"]]
        else:
            argv = ["run", *argv]
    raise SystemExit(main(argv))
