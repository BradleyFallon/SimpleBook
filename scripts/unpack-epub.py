#!/usr/bin/env python3
"""Unpack an EPUB to a directory for inspection."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys
import zipfile

PROJECT_ROOT = Path(__file__).resolve().parent.parent
NORMALIZER_DIR = PROJECT_ROOT / "src"
TEST_EPUBS_DIR = PROJECT_ROOT / "tests" / "epubs"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Unpack an EPUB to a directory for inspection.",
    )
    parser.add_argument(
        "book_or_path",
        nargs="?",
        help="Book key (e.g., frankenstein) or EPUB path.",
    )
    parser.add_argument(
        "--out",
        help="Output directory (default: ./unpacked/<name>).",
    )
    parser.add_argument(
        "--clean",
        action="store_true",
        help="Remove the output directory before extracting.",
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


def resolve_epub(arg: str) -> Path:
    books = build_books()
    if arg in books:
        return books[arg].resolve()
    return Path(arg).expanduser().resolve()


def default_out_dir(arg: str, epub_path: Path) -> Path:
    books = build_books()
    name = arg if arg in books else epub_path.stem
    return PROJECT_ROOT / "unpacked" / name


def main() -> int:
    args = parse_args()
    if args.list:
        books = build_books()
        for key in sorted(books.keys()):
            print(key)
        return 0

    if not args.book_or_path:
        print("Missing book key or EPUB path. Use --list to see available keys.")
        return 1
    epub_path = resolve_epub(args.book_or_path)

    if not epub_path.exists():
        print(f"EPUB not found: {epub_path}")
        return 1

    out_dir = Path(args.out).expanduser().resolve() if args.out else default_out_dir(args.book_or_path, epub_path)

    if out_dir.exists() and args.clean:
        for path in sorted(out_dir.rglob('*'), reverse=True):
            if path.is_file() or path.is_symlink():
                path.unlink()
            elif path.is_dir():
                path.rmdir()
        if out_dir.exists():
            out_dir.rmdir()

    out_dir.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(epub_path, 'r') as zf:
        zf.extractall(out_dir)

    print(f"OK: unpacked to {out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
