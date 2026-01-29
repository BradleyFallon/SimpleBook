#!/usr/bin/env python3
"""Run the full test suite."""

from __future__ import annotations

import subprocess
import sys


def main() -> int:
    cmd = [sys.executable, "-m", "pytest", "-q"]
    return subprocess.call(cmd)


if __name__ == "__main__":
    raise SystemExit(main())
