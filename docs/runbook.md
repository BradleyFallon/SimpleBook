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

Golden files live in `tests/*.json`.

## Debug a Book

Dump metadata + per-spine-item classification (headings/label/paragraph count):

```bash
debug-epub frankenstein --out frankenstein_debug.json
```

## Unpack an EPUB for Inspection

```bash
unpack-epub frankenstein
```

Unpacked files will be under `unpacked/<book-key>`.

## Notes

- EPUBs are stored in `tests/epubs/`.
- Source code lives in `src/`.
- Docs live in `docs/`.
