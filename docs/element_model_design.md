# Element-Based Normalization Design

This document proposes replacing the current paragraph‑centric model with an
**element‑centric model** to better capture EPUB structure (blockquotes, tables,
lists, headings) in a deterministic, parsable JSON format.

## Goals

- Preserve meaningful HTML structure in a **clean, deterministic** JSON shape.
- Make downstream parsing reliable for LLM training and data mining.
- Handle edge cases (e.g., Gatsby chapter 9) without custom hacks.
- Keep chunking deterministic and explainable.

## Non‑Goals

- Perfect reconstruction of visual layout.
- Support for malformed EPUBs (we accept a quality baseline).
- Semantic NLP (we only use HTML structure + basic text normalization).

## Proposed Output Shape

Previous: chapters → `pp` (paragraph strings) + `chunks` (indices).

Proposed: chapters → `elements` (typed entries) + `chunks` (indices).

```json
{
  "metadata": { "...": "..." },
  "chapters": [
    {
      "name": "Chapter 9",
      "elements": [
        { "type": "paragraph", "text": "..." },
        { "type": "blockquote", "text": "..." },
        { "type": "table", "rows": [["Rise from bed","6:00","a.m."], ...] },
        { "type": "cite", "text": "Shakespeare" }
      ],
      "chunks": [0, 2, 3]
    }
  ]
}
```

### Element Fields

- `type`: required, one of the supported element types.
- `text`: optional, used for most elements.
- `rows`: optional, used for table elements.
- `meta`: optional future‑proof field for attributes (e.g., `lang`, `class`).

## Element Types (Initial Set)

**Block / text‑bearing:**
- `paragraph` ← `<p>`
- `blockquote` ← `<blockquote>` (joined text)
- `list_item` ← `<li>`
- `heading` ← `<h1..h6>`
- `cite` ← `<cite>`

**Structured:**
- `table` ← `<table>` with `rows` (strings per cell)
- `definition_term` ← `<dt>`
- `definition_desc` ← `<dd>`

**Captions:**
- `caption` ← `<caption>` / `<figcaption>`

We can extend the set later if tests reveal more valid structures.

## Extraction Rules (HTML → Elements)

1. Use `get_body_content()` from ebooklib where available.
2. Strip non‑content elements (`script`, `style`, `nav`).
3. Traverse block‑level containers in document order.
4. Emit element records based on tags above.
5. **Error handling:** if a block‑level element with meaningful text is
   encountered and it is **not** in the supported tag set, raise
   `NotImplementedError` so we can explicitly add support (or decide to ignore).
6. Ignore text nodes that do not live inside supported tags.

### Tables

- Extract row/column text to `rows: list[list[str]]`.
- Each cell text is normalized with `_clean_text`.
- Tables should produce **one element** (chunked separately).

### Blockquotes

- Produce a `blockquote` element containing all text.
- A nested `<cite>` should be split into its own `cite` element.

## Chunking Rules (Elements → Chunks)

Chunk indices reference positions in `elements`.

Baseline:
- `table` → always starts a new chunk (and is a chunk on its own).
- `blockquote` → starts a new chunk (and may be its own chunk).
- `heading` → starts a new chunk.
- Otherwise, combine sequential `paragraph` / `list_item` until size limit.

Size limit (deterministic):
- Target char window (e.g. 1200), same as today.
- Do not split individual elements.

## Normalization Rules (Element Text)

Apply `_clean_text` to all `text` and each table cell.

Future (explicit):
- Normalize quote styles for dialogue (e.g. `<< >>`), only after
  a deterministic rule is defined.
- Preserve inline emphasis only if needed (currently ignored).

## Testing Strategy

**Extraction contract tests**
- All body text must be captured by supported tags.
  (existing `tests/extraction/test_body_coverage.py`).

**Normalization samples**
- Per‑book element samples with `raw` and `expected`.
- Regression tests compare normalized text against expected.

**Chunking tests**
- Ensure blockquotes/tables start new chunks.
- Ensure element index ordering stable across runs.

## Migration Plan

1. Implement element extraction in parallel (new `elements` field).
2. Update chunking to work on elements.
3. Update schema + golden files.
4. Update downstream tooling to the element model (complete).

## Open Questions

- Should `<cite>` be nested in `blockquote` or emitted as its own element?
- Should headings be included as elements or only as chapter `name`?
- Table representation: keep `rows` only, or also include a flattened `text`?
- Dialogue normalization: global or heuristic‑based?
