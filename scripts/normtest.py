#!/usr/bin/env python3
"""Run normalization tests."""

from __future__ import annotations

import subprocess
import sys


def main() -> int:
    cmd = [
        sys.executable,
        "-m",
        "pytest",
        "tests/normalization/test_cases_yaml.py",
        "tests/normalization/test_normalizer_samples.py",
        "-q",
    ]
    return subprocess.call(cmd)


if __name__ == "__main__":
    raise SystemExit(main())
