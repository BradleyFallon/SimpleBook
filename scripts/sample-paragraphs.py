#!/usr/bin/env python3
"""Generate element normalization samples from all test EPUBs."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import random
import sys

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SRC_DIR = PROJECT_ROOT / "src"
TEST_EPUBS_DIR = PROJECT_ROOT / "tests" / "epubs"
DEFAULT_JSON_DIR = PROJECT_ROOT / "tests" / "normalization" / "json"
DEFAULT_JSONL_OUT = PROJECT_ROOT / "tests" / "normalization" / "normalizer_samples.jsonl"
DEFAULT_TEXT_OUT = PROJECT_ROOT / "tests" / "normalization" / "normalizer_samples.txt"

sys.path.insert(0, str(SRC_DIR))

from bs4 import BeautifulSoup  # type: ignore[import-untyped]  # noqa: E402
from simplebook.main import (  # noqa: E402
    EbookContent,
    STRIP_ELEMENTS,
    _clean_text,
    ELEMENT_TAG_TYPES,
    HEADING_TAGS,
    CONTAINER_TAGS,
    TABLE_CELL_TAGS,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Sample one random element per chapter from each EPUB.",
    )
    parser.add_argument(
        "--out",
        type=Path,
        help=(
            "Output directory for JSON (default: "
            f"{DEFAULT_JSON_DIR}) or file path for JSONL/text outputs."
        ),
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=1337,
        help="Random seed for reproducible sampling.",
    )
    parser.add_argument(
        "--jsonl",
        action="store_true",
        help="Write JSONL output instead of pretty JSON.",
    )
    parser.add_argument(
        "--text",
        action="store_true",
        help="Write plain text output instead of JSON.",
    )
    return parser.parse_args()


def _key_from_stem(stem: str) -> str:
    key = stem.lower().replace("_", "-").replace(" ", "-")
    key = "-".join(part for part in key.split("-") if part)
    return key


def _iter_epubs() -> list[Path]:
    if not TEST_EPUBS_DIR.exists():
        return []
    return sorted(TEST_EPUBS_DIR.glob("*.epub"))


def _extract_raw_elements(html: bytes | str) -> list[dict]:
    if isinstance(html, (bytes, bytearray)):
        html = html.decode("utf-8", errors="ignore")
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(STRIP_ELEMENTS):
        tag.decompose()

    root = soup.body if soup.body is not None else soup
    samples: list[dict] = []

    def walk(node) -> None:
        for child in node.children:
            if not hasattr(child, "name") or child.name is None:
                continue
            name = child.name.lower()
            if name in STRIP_ELEMENTS:
                continue
            if name in CONTAINER_TAGS:
                walk(child)
                continue
            if name in HEADING_TAGS:
                raw = child.get_text("\n")
                if raw.strip():
                    samples.append(
                        {"type": "heading", "raw": raw, "expected": _clean_text(raw)}
                    )
                continue
            if name == "blockquote":
                parts = []
                for text in child.find_all(string=True):
                    if not text or not text.strip():
                        continue
                    if text.find_parent("cite"):
                        continue
                    parts.append(str(text))
                raw = "\n".join(parts)
                if raw.strip():
                    samples.append(
                        {"type": "blockquote", "raw": raw, "expected": _clean_text(raw)}
                    )
                for cite in child.find_all("cite"):
                    cite_raw = cite.get_text("\n")
                    if cite_raw.strip():
                        samples.append(
                            {"type": "cite", "raw": cite_raw, "expected": _clean_text(cite_raw)}
                        )
                continue
            if name == "table":
                for tr in child.find_all("tr"):
                    for cell in tr.find_all(list(TABLE_CELL_TAGS)):
                        raw = cell.get_text("\n")
                        if raw.strip():
                            samples.append(
                                {"type": "table_cell", "raw": raw, "expected": _clean_text(raw)}
                            )
                continue
            if name in ELEMENT_TAG_TYPES:
                raw = child.get_text("\n")
                if raw.strip():
                    samples.append(
                        {"type": ELEMENT_TAG_TYPES[name], "raw": raw, "expected": _clean_text(raw)}
                    )
                continue

    walk(root)
    return samples


def _sample_paragraphs(epub_path: Path, rng: random.Random) -> list[dict]:
    source = EbookContent(str(epub_path))
    source.load()
    source.classify_spine_items()

    samples: list[dict] = []
    for idx, item in enumerate(source.chapter_items()):
        raw_elements = _extract_raw_elements(item.get_content())
        if not raw_elements:
            continue
        element_index = rng.randrange(len(raw_elements))
        sample = raw_elements[element_index]
        samples.append(
            {
                "book": _key_from_stem(epub_path.stem),
                "chapter_index": idx,
                "chapter_name": source.item_name(item),
                "element_index": element_index,
                "element_type": sample["type"],
                "raw": sample["raw"],
                "expected": sample["expected"],
            }
        )
    return samples


def _write_text(out_path: Path, samples: list[dict]) -> None:
    lines: list[str] = []
    for sample in samples:
        header = (
            f"[{sample['book']}] {sample['chapter_index']}: "
            f"{sample['chapter_name']} (e{sample['element_index']}:{sample['element_type']})"
        )
        lines.append(header)
        lines.append("RAW:")
        lines.append(sample["raw"])
        lines.append("")
        lines.append("EXPECTED:")
        lines.append(sample["expected"])
        lines.append("")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(lines).strip() + "\n", encoding="utf-8")


def _write_jsonl(out_path: Path, samples: list[dict]) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as handle:
        for sample in samples:
            handle.write(json.dumps(sample, ensure_ascii=False) + "\n")


def _write_json(out_dir: Path, samples: list[dict]) -> None:
    by_book: dict[str, list[dict]] = {}
    for sample in samples:
        key = sample.get("book", "unknown")
        by_book.setdefault(key, []).append(sample)

    out_dir.mkdir(parents=True, exist_ok=True)
    for book, items in sorted(by_book.items()):
        path = out_dir / f"{book}.json"
        path.write_text(
            json.dumps(items, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )


def main() -> int:
    args = parse_args()
    epubs = _iter_epubs()
    if not epubs:
        print(f"No EPUBs found in {TEST_EPUBS_DIR}", file=sys.stderr)
        return 1

    rng = random.Random(args.seed)
    samples: list[dict] = []
    for epub_path in epubs:
        samples.extend(_sample_paragraphs(epub_path, rng))

    if args.text:
        out_path = args.out or DEFAULT_TEXT_OUT
        _write_text(out_path, samples)
    elif args.jsonl:
        out_path = args.out or DEFAULT_JSONL_OUT
        _write_jsonl(out_path, samples)
    else:
        out_dir = args.out or DEFAULT_JSON_DIR
        _write_json(out_dir, samples)

    target = args.out or (DEFAULT_TEXT_OUT if args.text else DEFAULT_JSONL_OUT if args.jsonl else DEFAULT_JSON_DIR)
    print(f"OK: wrote {len(samples)} samples to {target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
