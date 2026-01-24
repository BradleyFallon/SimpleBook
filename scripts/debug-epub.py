#!/usr/bin/env python3
"""Dump EPUB debug info (metadata + spine item classification)."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parent.parent
NORMALIZER_DIR = PROJECT_ROOT / "src"
TEST_EPUBS_DIR = PROJECT_ROOT / "tests" / "epubs"

sys.path.insert(0, str(NORMALIZER_DIR))

from bs4 import BeautifulSoup  # type: ignore[import-untyped]  # noqa: E402
from simplebook.main import (  # noqa: E402
    EbookContent,
    STRIP_ELEMENTS,
    _classify_label_type,
    _extract_heading_texts,
    _extract_elements,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Dump EPUB info for debugging heuristics.",
    )
    parser.add_argument(
        "book_or_path",
        nargs="?",
        help="Book key (e.g., the-hobbit) or EPUB path.",
    )
    parser.add_argument(
        "--out",
        help="Write JSON output to this path instead of stdout.",
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


def classify_item(label_text: str | None, element_count: int) -> tuple[str, str]:
    label_type = _classify_label_type(label_text)
    if label_type in {"front", "back"}:
        return label_type, "label_keyword"
    if label_type == "chapter":
        return "chapter", "heading_match"
    if element_count >= 10:
        return "chapter", "element_count>=10"
    return "other", "fallback"


def debug_item(content_bytes: bytes) -> dict:
    soup = BeautifulSoup(content_bytes, "html.parser")
    for tag in soup(STRIP_ELEMENTS):
        tag.decompose()

    heading_texts = _extract_heading_texts(soup)
    label_text = " - ".join(heading_texts) if heading_texts else None

    elements = _extract_elements(soup)
    element_count = sum(1 for el in elements if el.text_length() > 0)

    item_type, reason = classify_item(label_text, element_count)

    return {
        "headings": heading_texts,
        "label": label_text,
        "element_count": element_count,
        "type": item_type,
        "reason": reason,
    }


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

    book = EbookContent(str(epub_path))
    book.load()

    metadata = {
        "title": (book.get_metadata("DC", "title") or [[None]])[0][0] or "",
        "author": (book.get_metadata("DC", "creator") or [[None]])[0][0] or "",
        "language": (book.get_metadata("DC", "language") or [[None]])[0][0] or "",
        "identifiers": [val for val, _attrs in book.get_metadata("DC", "identifier")],
    }

    items = []
    for idx, item in enumerate(book.items):
        info = debug_item(item.get_content())
        items.append(
            {
                "index": idx,
                "id": getattr(item, "get_id", lambda: None)(),
                "name": getattr(item, "get_name", lambda: None)(),
                "media_type": getattr(item, "media_type", None),
                **info,
            }
        )

    payload = {
        "path": str(epub_path),
        "metadata": metadata,
        "spine_items": items,
    }

    if args.out:
        out_path = Path(args.out).expanduser().resolve()
        out_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"OK: wrote {out_path}")
        return 0

    print(json.dumps(payload, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
