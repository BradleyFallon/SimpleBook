"""
Validate preview output for every EPUB in tests/epubs against the schema.
"""

from __future__ import annotations

from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_DIR = PROJECT_ROOT / "src"
sys.path.insert(0, str(SRC_DIR))

from simplebook import SimpleBook  # noqa: E402
from simplebook.schema_validator import validate_output  # noqa: E402

TEST_EPUBS_DIR = PROJECT_ROOT / "tests" / "epubs"


def _iter_epubs() -> list[Path]:
    if not TEST_EPUBS_DIR.exists():
        return []
    return sorted(TEST_EPUBS_DIR.glob("*.epub"))


def test_all_epubs_schema() -> None:
    epubs = _iter_epubs()
    assert epubs, f"No EPUBs found in {TEST_EPUBS_DIR}"

    failures: list[tuple[str, list[str]]] = []

    for epub_path in epubs:
        book = SimpleBook()
        try:
            book.load_epub(str(epub_path))
            output = book.serialize(preview=True)
            is_valid, errors = validate_output(output)
            if not is_valid:
                failures.append((epub_path.name, errors))
        except Exception as exc:  # pragma: no cover - explicit reporting
            failures.append((epub_path.name, [f"exception: {exc}"]))

    if failures:
        print("Schema validation failures:")
        for name, errors in failures:
            print(f"- {name} ({len(errors)} errors)")
            for err in errors:
                print(f"  - {err}")
        assert False, f"Schema validation failed for {len(failures)} EPUB(s)."


if __name__ == "__main__":
    try:
        test_all_epubs_schema()
    except AssertionError as exc:
        raise SystemExit(str(exc))
