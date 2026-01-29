#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import sys
import statistics

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_DIR = PROJECT_ROOT / "src"
sys.path.insert(0, str(SRC_DIR))

from simplebook.main import EbookNormalizer, SimpleBook  # noqa: E402


def _select_demo_chapter(book: SimpleBook):
    for chapter in book.chapters:
        name = (chapter.label or "").lower()
        if "chapter" in name:
            return chapter
    return book.chapters[0] if book.chapters else None


def _histogram(values: list[int], edges: list[int]) -> list[tuple[str, int]]:
    if not values:
        return []
    if not edges:
        raise ValueError("Histogram edges cannot be empty.")
    bins: list[tuple[str, int]] = []

    def label_for(start: int, end: int | None) -> str:
        if end is None:
            return f"{start}+"
        if start == end:
            return f"{start}"
        return f"{start}-{end}"

    for idx, start in enumerate(edges):
        end = edges[idx + 1] - 1 if idx + 1 < len(edges) else None
        if end is None:
            count = sum(1 for value in values if value >= start)
        else:
            count = sum(1 for value in values if start <= value <= end)
        bins.append((label_for(start, end), count))
    return bins


def _stat_block(values: list[int]) -> str:
    if not values:
        return "n/a"
    mean = statistics.mean(values)
    median = statistics.median(values)
    modes = statistics.multimode(values)
    mode_text = ", ".join(str(mode) for mode in modes) if modes else "n/a"
    return (
        f"{min(values):>6} {max(values):>6} {mean:>8.2f} "
        f"{median:>8.2f} {mode_text:>10}"
    )


def _element_type_counts(chapter) -> dict[str, int]:
    counts: dict[str, int] = {}
    for element in chapter.elements:
        counts[element.type] = counts.get(element.type, 0) + 1
    return dict(sorted(counts.items()))


def _print_kv_row(label: str, value: str | int) -> None:
    print(f"{label:<22} {value}")


def _print_histogram(title: str, values: list[int], edges: list[int]) -> None:
    print(f"\n{title}:")
    print(f"{'min':>6} {'max':>6} {'mean':>8} {'median':>8} {'mode':>10}")
    print(_stat_block(values))
    if not values:
        return
    print(f"{'bucket':>12} {'count':>7} {'bar'}")
    for bucket, count in _histogram(values, edges=edges):
        bar = "=" * min(count, 40)
        print(f"{bucket:>12} {count:>7} {bar}")


def _print_stats(chapter, label: str) -> None:
    chunk_count = len(chapter.chunks)
    elements_per_chunk = [len(chunk.elements) for chunk in chapter.chunks]
    words_per_chunk = [chunk.word_count() for chunk in chapter.chunks]
    element_words = [element.word_count() for element in chapter.elements]

    print(f"\n=== Chunk Stats ({label}) ===")
    _print_kv_row("Chapter", chapter.label or "Untitled")
    _print_kv_row("Total elements", len(chapter.elements))
    _print_kv_row("Total chunks", chunk_count)

    element_edges = [1, 2, 3, 5, 10, 15, 20, 30,
                     40, 50, 75, 100, 150, 200, 300, 400, 500]
    word_edges = [1, 2, 3, 5, 10, 25, 50, 75,
                  100, 150, 200, 250, 300, 400, 500, 1000]
    _print_histogram("Elements per chunk",
                     elements_per_chunk, edges=element_edges)
    _print_histogram("Words per chunk", words_per_chunk, edges=word_edges)
    _print_histogram("Element word counts", element_words, edges=element_edges)

    print("\nElement type counts:")
    for element_type, count in _element_type_counts(chapter).items():
        print(f"  {element_type:<18} {count:>6}")


def main() -> int:
    epub_path = PROJECT_ROOT / "tests" / "epubs" / "The_Hobbit.epub"
    if not epub_path.exists():
        print(f"EPUB not found: {epub_path}")
        return 1

    normalizer = EbookNormalizer()
    normalizer.run_all(str(epub_path))

    chapter = _select_demo_chapter(normalizer.simple_book)
    if chapter is None:
        print("No chapters found in demo EPUB.")
        return 1

    manual_book = SimpleBook()
    manual_book.metadata = normalizer.simple_book.metadata
    manual_book.chapters = [chapter]

    out_path = Path(__file__).resolve().parent / "chunking_form.txt"
    _print_stats(chapter, "before manual edits")
    manual_book.export_chunk_form(str(out_path))

    print(f"chunking file saved to: {out_path}")
    print("please insert chunk separators and save, then press enter to continue")
    input()
    print("reading chunk separators...")
    manual_book.import_chunk_form(str(out_path))
    _print_stats(chapter, "after manual edits")
    print("done")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
