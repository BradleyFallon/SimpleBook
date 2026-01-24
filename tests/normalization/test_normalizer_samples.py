"""
Verify normalized paragraph samples against expected output.
"""

from __future__ import annotations

import json
from pathlib import Path

from simplebook.main import _clean_text

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SAMPLES_DIR = PROJECT_ROOT / "tests" / "normalization" / "json"
SAMPLES_JSONL = PROJECT_ROOT / "tests" / "normalization" / "normalizer_samples.jsonl"


def _iter_samples() -> list[dict]:
    samples: list[dict] = []
    if SAMPLES_DIR.exists():
        for path in sorted(SAMPLES_DIR.glob("*.json")):
            data = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(data, list):
                samples.extend(data)
    if samples:
        return samples
    if not SAMPLES_JSONL.exists():
        return []
    for line in SAMPLES_JSONL.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        samples.append(json.loads(line))
    return samples


def test_normalizer_samples() -> None:
    samples = _iter_samples()
    assert samples, f"Missing samples files in {SAMPLES_DIR} or {SAMPLES_JSONL}"

    failures: list[str] = []
    for sample in samples:
        raw = sample.get("raw", "")
        expected = sample.get("expected", "")
        actual = _clean_text(raw)
        if actual != expected:
            element_index = sample.get("element_index", sample.get("paragraph_index"))
            element_type = sample.get("element_type", "paragraph")
            ident = (
                f"{sample.get('book')}::"
                f"{sample.get('chapter_index')}::"
                f"{element_index}::"
                f"{element_type}"
            )
            failures.append(
                f"{ident} expected {expected!r} got {actual!r}"
            )

    if failures:
        preview = "\n".join(failures[:10])
        raise AssertionError(
            f"{len(failures)} normalization sample(s) failed.\n{preview}"
        )
