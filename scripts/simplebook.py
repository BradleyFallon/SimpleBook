#!/usr/bin/env python3
"""SimpleBook CLI wrapper for local development."""

from __future__ import annotations

from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SRC_DIR = PROJECT_ROOT / "src"
sys.path.insert(0, str(SRC_DIR))

from simplebook.cli import main  # noqa: E402


if __name__ == "__main__":
    raise SystemExit(main())
