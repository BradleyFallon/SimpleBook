"""Command-line interface for SimpleBook."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from .main import EbookNormalizer
from .schema_validator import load_schema, validate_output


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="simplebook",
        description="Normalize an EPUB into the SimpleBook JSON format.",
    )
    parser.add_argument(
        "epub",
        help="Path to the EPUB file.",
    )
    parser.add_argument(
        "-o",
        "--out",
        help="Write JSON output to this file (defaults to stdout).",
    )
    parser.add_argument(
        "--preview",
        action="store_true",
        help="Emit chapter structure and chunk indices only (omit paragraphs).",
    )
    parser.add_argument(
        "--validate",
        action="store_true",
        help="Validate output against the JSON schema.",
    )
    parser.add_argument(
        "--schema",
        help="Path to a JSON schema file (defaults to bundled schema).",
    )
    return parser.parse_args(argv)


def _load_schema(schema_path: str | None) -> dict:
    if not schema_path:
        return load_schema()
    path = Path(schema_path).expanduser().resolve()
    if not path.exists():
        raise FileNotFoundError(f"Schema file not found: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    epub_path = Path(args.epub).expanduser().resolve()

    if not epub_path.exists():
        print(f"EPUB not found: {epub_path}", file=sys.stderr)
        return 1

    normalizer = EbookNormalizer()
    data = normalizer.run_all(str(epub_path), preview=args.preview)

    if args.validate:
        try:
            schema = _load_schema(args.schema)
            is_valid, errors = validate_output(data, schema)
        except Exception as exc:  # pragma: no cover - explicit CLI error path
            print(f"Schema validation failed: {exc}", file=sys.stderr)
            return 1
        if not is_valid:
            print("Schema validation errors:", file=sys.stderr)
            for error in errors:
                print(f"- {error}", file=sys.stderr)
            return 1

    output = json.dumps(data, indent=2, ensure_ascii=False)

    if args.out:
        out_path = Path(args.out).expanduser().resolve()
        out_path.write_text(output, encoding="utf-8")
        print(f"OK: wrote {out_path}")
        return 0

    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
