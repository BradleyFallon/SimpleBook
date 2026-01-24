# Extraction Rules

This document defines the **input quality contract** and extraction rules for
SimpleBook. These rules determine how elements are extracted from EPUB HTML
before normalization.

## Input Quality Contract

We support EPUBs that encode paragraph text using semantic block elements.
At minimum, narrative paragraphs should be in `<p>` tags. We also accept
common structured text tags such as:

- `<cite>` (epigraph attributions)
- `<li>` (lists)
- `<dt>` / `<dd>` (definition lists)
- `<td>` / `<th>` (table cells)
- `<figcaption>` / `<caption>` (figure/table captions)

If an EPUB uses non-semantic layouts (e.g., dense `<br>` usage, stray text
nodes, or styling-based paragraphs), it is considered **out of scope**.

## Extraction (Current)

- Elements are extracted from the tag set above.
- Headings are used for chapter naming and are also captured as `heading` elements.
- Text outside the allowed tag set is ignored.
- Unsupported elements that contain text raise `NotImplementedError`.

## Enforcement Tests

The extraction contract is enforced by:

- `tests/extraction/test_body_coverage.py`
  - Ensures all non-heading text in the body is contained inside allowed tags.
  - Ensures extracted element text covers at least 95% of the body text (excluding headings).

If these tests fail, the EPUB is considered malformed or out of scope.
