"""
Validate normalization rules defined in tests/normalization/cases.yaml.
"""

from __future__ import annotations

from pathlib import Path
import sys

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_DIR = PROJECT_ROOT / "src"
sys.path.insert(0, str(SRC_DIR))

from simplebook.main import _clean_text  # noqa: E402

CASES_PATH = PROJECT_ROOT / "tests" / "normalization" / "cases.yaml"


def _load_cases() -> list[dict]:
    if not CASES_PATH.exists():
        return []
    data = yaml.safe_load(CASES_PATH.read_text(encoding="utf-8"))
    if not data:
        return []
    if not isinstance(data, list):
        raise AssertionError("Normalization cases must be a list of rules.")
    return data


def test_normalization_cases_yaml() -> None:
    rules = _load_cases()
    assert rules, f"Missing cases file: {CASES_PATH}"

    failures: list[str] = []
    for rule in rules:
        rule_id = rule.get("id", "<missing-id>")
        examples = rule.get("examples", [])
        if not isinstance(examples, list) or not examples:
            failures.append(f"{rule_id} has no examples")
            continue
        for idx, example in enumerate(examples, start=1):
            raw = example.get("input", "")
            expected = example.get("expected", "")
            actual = _clean_text(raw)
            if actual != expected:
                failures.append(
                    f"{rule_id}[{idx}] expected {expected!r} got {actual!r}"
                )

    if failures:
        preview = "\n".join(failures[:10])
        raise AssertionError(
            f"{len(failures)} normalization case(s) failed.\n{preview}"
        )
