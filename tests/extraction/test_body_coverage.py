"""
Ensure chapter body text is captured by element extraction.
"""

from __future__ import annotations

from pathlib import Path
import sys

from bs4 import BeautifulSoup, Comment  # type: ignore[import-untyped]

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_DIR = PROJECT_ROOT / "src"
sys.path.insert(0, str(SRC_DIR))

from simplebook.main import (  # noqa: E402
    EbookContent,
    STRIP_ELEMENTS,
    _clean_text,
    _extract_elements,
    ALLOWED_TEXT_TAGS,
    HEADING_TAGS,
)

TEST_EPUBS_DIR = PROJECT_ROOT / "tests" / "epubs"


def _collapse_ws(text: str) -> str:
    return " ".join(text.split())


def _iter_epubs() -> list[Path]:
    if not TEST_EPUBS_DIR.exists():
        return []
    return sorted(TEST_EPUBS_DIR.glob("*.epub"))


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


def _paragraph_text(soup: BeautifulSoup) -> str:
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


def _body_text_without_headings(soup: BeautifulSoup) -> str:
    parts: list[str] = []
    for text in _text_nodes(soup):
        if _has_ancestor(text, HEADING_TAGS):
            continue
        parts.append(str(text))
    cleaned = _clean_text("\n".join(parts))
    return _collapse_ws(cleaned)


def test_body_text_coverage() -> None:
    epubs = _iter_epubs()
    assert epubs, f"No EPUBs found in {TEST_EPUBS_DIR}"

    failures: list[str] = []

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
            if stray_nodes:
                preview = "; ".join(_collapse_ws(str(text))[:120] for text in stray_nodes[:3])
                failures.append(
                    f"{epub_path.name} chapter[{idx}] has stray text outside allowed tags: {preview}"
                )

            body_text = _body_text_without_headings(soup)
            try:
                para_text = _paragraph_text(soup)
            except NotImplementedError as exc:
                failures.append(
                    f"{epub_path.name} chapter[{idx}] unsupported element: {exc}"
                )
                continue
            if body_text:
                ratio = len(para_text) / len(body_text)
                if ratio < 0.95:
                    failures.append(
                        f"{epub_path.name} chapter[{idx}] paragraph coverage {ratio:.2f} (< 0.95)"
                    )

    if failures:
        details = "\n".join(failures[:20])
        raise AssertionError(f"{len(failures)} body coverage issue(s):\n{details}")
