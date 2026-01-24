#!/usr/bin/env python3
"""Unpack all test EPUBs into tests/epubs/unpacked."""

from __future__ import annotations

import argparse
from pathlib import Path
import zipfile

PROJECT_ROOT = Path(__file__).resolve().parent.parent
TEST_EPUBS_DIR = PROJECT_ROOT / "tests" / "epubs"
UNPACKED_DIR = TEST_EPUBS_DIR / "unpacked"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Unpack all EPUBs in tests/epubs to tests/epubs/unpacked.",
    )
    parser.add_argument(
        "--clean",
        action="store_true",
        help="Remove existing unpacked directories before extracting.",
    )
    return parser.parse_args()


def _key_from_stem(stem: str) -> str:
    key = stem.lower().replace("_", "-").replace(" ", "-")
    key = "-".join(part for part in key.split("-") if part)
    return key


def _clean_dir(path: Path) -> None:
    if not path.exists():
        return
    for sub in sorted(path.rglob("*"), reverse=True):
        if sub.is_file() or sub.is_symlink():
            sub.unlink()
        elif sub.is_dir():
            sub.rmdir()
    if path.exists():
        path.rmdir()


def main() -> int:
    args = parse_args()
    if not TEST_EPUBS_DIR.exists():
        print(f"No test EPUB directory found: {TEST_EPUBS_DIR}")
        return 1

    epubs = sorted(TEST_EPUBS_DIR.glob("*.epub"))
    if not epubs:
        print(f"No EPUBs found in {TEST_EPUBS_DIR}")
        return 1

    UNPACKED_DIR.mkdir(parents=True, exist_ok=True)

    for epub_path in epubs:
        name = _key_from_stem(epub_path.stem)
        out_dir = UNPACKED_DIR / name
        if args.clean:
            _clean_dir(out_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(epub_path, "r") as zf:
            zf.extractall(out_dir)
        print(f"OK: unpacked {epub_path.name} -> {out_dir}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
