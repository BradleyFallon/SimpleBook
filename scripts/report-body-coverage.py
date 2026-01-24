#!/usr/bin/env python3
"""Report extraction coverage for all chapter items."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

from bs4 import BeautifulSoup, Comment  # type: ignore[import-untyped]

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SRC_DIR = PROJECT_ROOT / "src"
TEST_EPUBS_DIR = PROJECT_ROOT / "tests" / "epubs"

sys.path.insert(0, str(SRC_DIR))

from simplebook.main import (  # noqa: E402
    ALLOWED_TEXT_TAGS,
    HEADING_TAGS,
    STRIP_ELEMENTS,
    EbookContent,
    _clean_text,
    _extract_elements,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Report paragraph/element coverage for EPUB chapter items.",
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=0.95,
        help="Minimum acceptable coverage ratio (default: 0.95).",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Show all chapters, not just failures.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=20,
        help="Max number of failing chapters to print (default: 20).",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit with status 1 if any failures are found.",
    )
    return parser.parse_args()


def _iter_epubs() -> list[Path]:
    if not TEST_EPUBS_DIR.exists():
        return []
    return sorted(TEST_EPUBS_DIR.glob("*.epub"))


def _collapse_ws(text: str) -> str:
    return " ".join(text.split())


def _parse_body_html(item) -> BeautifulSoup:
    if hasattr(item, "get_body_content"):
        html = item.get_body_content()
    else:
        html = item.get_content()
    if isinstance(html, (bytes, bytearray)):
        html = html.decode("utf-8", errors="ignore")
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(STRIP_ELEMENTS):
        tag.decompose()
    return soup


def _text_nodes(soup: BeautifulSoup):
    for text in soup.find_all(string=True):
        if not text or not text.strip():
            continue
        if isinstance(text, Comment):
            continue
        parent = text.parent
        if not parent:
            continue
        if parent.name in STRIP_ELEMENTS:
            continue
        yield text


def _has_ancestor(text, tags: set[str]) -> bool:
    return text.find_parent(tags) is not None


def _body_text_without_headings(soup: BeautifulSoup) -> str:
    parts: list[str] = []
    for text in _text_nodes(soup):
        if _has_ancestor(text, HEADING_TAGS):
            continue
        parts.append(str(text))
    cleaned = _clean_text("\n".join(parts))
    return _collapse_ws(cleaned)


def _element_text(soup: BeautifulSoup) -> str:
    elements = _extract_elements(soup)
    parts: list[str] = []
    for element in elements:
        if element.text:
            parts.append(element.text)
        if element.rows:
            for row in element.rows:
                parts.append(" ".join(cell for cell in row if cell))
    cleaned = _clean_text("\n\n".join(p for p in parts if p.strip()))
    return _collapse_ws(cleaned)


def main() -> int:
    args = parse_args()
    epubs = _iter_epubs()
    if not epubs:
        print(f"No EPUBs found in {TEST_EPUBS_DIR}")
        return 1

    failures = 0
    printed = 0

    for epub_path in epubs:
        source = EbookContent(str(epub_path))
        source.load()
        source.classify_spine_items()

        for idx, item in enumerate(source.chapter_items()):
            soup = _parse_body_html(item)

            stray_nodes = [
                text
                for text in _text_nodes(soup)
                if not _has_ancestor(text, ALLOWED_TEXT_TAGS)
            ]
            stray_preview = "; ".join(_collapse_ws(str(text))[:120] for text in stray_nodes[:3])

            try:
                body_text = _body_text_without_headings(soup)
                element_text = _element_text(soup)
            except NotImplementedError as exc:
                failures += 1
                if args.all or printed < args.limit:
                    printed += 1
                    chapter_name = source.item_name(item)
                    print(
                        f"{epub_path.name} chapter[{idx}] {chapter_name} -> unsupported: {exc}"
                    )
                continue

            ratio = 1.0 if not body_text else len(element_text) / len(body_text)
            is_fail = stray_nodes or ratio < args.threshold
            if is_fail:
                failures += 1
            if args.all or (is_fail and printed < args.limit):
                printed += 1
                chapter_name = source.item_name(item)
                status = "FAIL" if is_fail else "OK"
                print(
                    f"{status} {epub_path.name} chapter[{idx}] {chapter_name} "
                    f"coverage={ratio:.2f} stray={len(stray_nodes)}"
                )
                if stray_preview:
                    print(f"  stray: {stray_preview}")

    if failures:
        print(f"\nFound {failures} chapter(s) below threshold or with stray text.")
        return 1 if args.strict else 0

    print("\nAll chapters meet coverage threshold.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
