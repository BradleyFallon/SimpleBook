#!/usr/bin/env python3
"""Golden-file regression test runner for preview output."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parent.parent
NORMALIZER_DIR = PROJECT_ROOT / "src"
TEST_EPUBS_DIR = PROJECT_ROOT / "tests" / "epubs"

sys.path.insert(0, str(NORMALIZER_DIR))

from simplebook import SimpleBook  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run preview-mode golden file regression tests.",
    )
    parser.add_argument(
        "name",
        nargs="?",
        help="Book key (e.g., the-hobbit).",
    )
    parser.add_argument(
        "--regen",
        action="store_true",
        help="Regenerate golden file from current output.",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List available book keys.",
    )
    return parser.parse_args()

def _key_from_stem(stem: str) -> str:
    key = stem.lower().replace("_", "-").replace(" ", "-")
    key = "-".join(part for part in key.split("-") if part)
    return key


def build_books() -> dict[str, Path]:
    books: dict[str, Path] = {}
    if not TEST_EPUBS_DIR.exists():
        return books
    for path in sorted(TEST_EPUBS_DIR.glob("*.epub")):
        key = _key_from_stem(path.stem)
        books[key] = path
    return books


def build_output(epub_path: Path) -> dict:
    book = SimpleBook()
    book.load_epub(str(epub_path))
    return book.serialize(preview=True)


def main() -> int:
    args = parse_args()
    if args.list:
        books = build_books()
        for key in sorted(books.keys()):
            print(key)
        return 0

    name = args.name
    if not name:
        print("Missing book key. Use --list to see available keys.")
        return 1
    books = build_books()

    if name not in books:
        available = ", ".join(sorted(books.keys()))
        print(f"Unknown book key: {name}")
        if available:
            print(f"Available: {available}")
        else:
            print(f"No EPUBs found in {TEST_EPUBS_DIR}")
        return 1

    epub_path = books[name].expanduser().resolve()
    if not epub_path.exists():
        print(f"EPUB not found: {epub_path}")
        return 1

    output = build_output(epub_path)
    golden_path = PROJECT_ROOT / "tests" / f"{name}.json"

    if args.regen:
        golden_path.write_text(
            json.dumps(output, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        print(f"OK: wrote golden file to {golden_path}")
        return 0

    if not golden_path.exists():
        print(f"Golden file missing: {golden_path}")
        print(f"Run: ./regtest.py {name} --regen")
        return 1

    expected = json.loads(golden_path.read_text(encoding="utf-8"))
    if output == expected:
        print("OK: output matches golden file.")
        return 0

    print("FAIL: output differs from golden file.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
