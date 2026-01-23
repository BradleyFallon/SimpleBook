# AGENTS

Project conventions for automation and helper scripts.

## Layout

- `src/` — core normalization code (package `simplebook`)
- `scripts/` — runnable helper scripts (Python)
- `tests/` — golden JSON outputs and `tests/epubs/`
- `docs/` — project documentation

## Scripts

All scripts are in `scripts/` and are executable Python files.

Common commands (via aliases loaded by `source ./activate`):

- `regtest` — run golden regression tests (preview mode)
- `debug-epub` — dump metadata and spine-item classification
- `unpack-epub` — unzip an EPUB for inspection

## Golden Files

- Golden JSON outputs live at `tests/<book-key>.json`.
- EPUB inputs live at `tests/epubs/`.
- Use `regtest --list` to see available book keys.
- Regenerate with `regtest <key> --regen`.

## Output Schema

- Schema is defined in `src/simplebook/output_schema.json`.
- `name` is required (non-empty string) for each chapter.
