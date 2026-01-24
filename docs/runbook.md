# SimpleBook Runbook

Common workflows for normalization, regression testing, and debugging.

## Quick Start

```bash
source ./activate
regtest --list
```

## Generate / Compare Golden Files

Generate (or update) a golden file for a book key:

```bash
regtest the-hobbit --regen
```

Compare against the existing golden:

```bash
regtest the-hobbit
```

Golden files live in `tests/schema/json/*.json`.

## Sample Elements (Normalizer Tests)

Generate per-book JSON files containing one random element per chapter per EPUB,
with raw and expected normalized versions:

```bash
sample-paragraphs
```

Output defaults to `tests/normalization/json/*.json`. Use JSONL output with:

```bash
sample-paragraphs --jsonl --out tests/normalization/normalizer_samples.jsonl
```

Plain text output:

```bash
sample-paragraphs --text --out tests/normalization/normalizer_samples.txt
```

## Normalization Rule Cases

Rules and examples live in `tests/normalization/cases.yaml`. Regenerate the
doc from cases with:

```bash
gen-normalization-docs
```

## Extraction Contract Tests

Verify that chapter body text is captured by `<p>` tags only:

```bash
pytest tests/extraction/test_body_coverage.py -q
```

Detailed report (coverage + stray text):

```bash
report-body-coverage --all
```

## Debug a Book

Dump metadata + per-spine-item classification (headings/label/paragraph count):

```bash
debug-epub frankenstein --out frankenstein_debug.json
```

## Unpack an EPUB for Inspection

```bash
unpack-epub frankenstein
```

Unpacked files will be under `tests/epubs/unpacked/<book-key>`.

## Unpack All EPUBs

```bash
unpack-all-epubs
```

Add `--clean` to remove each output directory before extraction.

## Notes

- EPUBs are stored in `tests/epubs/`.
- Source code lives in `src/`.
- Docs live in `docs/`.

## Publish to PyPI (minimal)

1. Ensure version is correct in `pyproject.toml`.
2. Build:

```bash
python -m pip install --upgrade build twine
python -m build
```

3. Upload:

```bash
python -m twine upload dist/*
```

Optional: test on TestPyPI first:

```bash
python -m twine upload --repository testpypi dist/*
```
