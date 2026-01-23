# SimpleBook

Status: active (deterministic EPUB normalizer + tools).

## Quick start

```bash
source ./activate
regtest --list
simplebook tests/epubs/the-hobbit.epub --preview -o /tmp/the-hobbit.json
simplebook tests/epubs/the-hobbit.epub --validate
gen-docs
```

## CLI

Run the normalizer with the installed command or the dev wrapper:

```bash
simplebook path/to/book.epub --preview --out /tmp/book.json
python -m simplebook path/to/book.epub --validate
scripts/simplebook.py path/to/book.epub
```

Flags:
- `--preview` outputs chapter structure/chunks only (omits paragraphs).
- `--out` writes JSON to a file instead of stdout.
- `--validate` validates output against the JSON schema.

Aliases and completions are loaded by `source ./activate` (see `devtools/aliases.sh`).

## Generated docs

Docs are generated into `docs/generated`. Regenerate anytime with:

```bash
gen-docs
```

## Purpose

Provide a **deterministic, no‑LLM** ingest + structuring pipeline that turns an EPUB into
canonical book structure (sections/chapters/chunks) plus normalized artifacts.

## Owns

- Container resolution + OPF parsing (EPUB2/3)
- TOC extraction (NCX + nav)
- Spine resolution + reading order
- Canonical text extraction (HTML/XHTML → text)
- Section/Chapter inference (deterministic)
- Chunking (paragraph/segment splitting)
- Asset index + manifest normalization
- Raw artifact capture (OPF/NCX/nav, source file map)

## Inputs

- EPUB file (zip)

## Outputs

- Normalized manifest JSON (stable schema)
- Structured content: sections → chapters → chunks
- Raw artifact capture (OPF, NCX, nav)
- Asset map (images/css/fonts) + cover reference

## Plan (deterministic, no LLMs)

1. **Resolve package**  
   - Read `META-INF/container.xml` → locate OPF.
   - Parse OPF 2.0/3.0 metadata, manifest, spine.

2. **Build reading order**  
   - Resolve spine items to hrefs; verify existence.
   - Collect candidate content files (.html/.xhtml).

3. **Extract navigation**  
   - Prefer EPUB3 nav (`toc.xhtml`), fallback to NCX.
   - Normalize to a single TOC list with labels + hrefs.

4. **Extract text deterministically**  
   - Parse XHTML/HTML.
   - Strip non-content elements (nav, scripts, styles, hidden).
   - Normalize whitespace; preserve basic structure (headings, paragraphs).

5. **Structure + chunk**  
   - Deterministically segment into **sections** (toc entries + headings).
   - Derive **chapters** from toc labels/heading levels when present.
   - Chunk text into stable sizes with paragraph boundaries.

6. **Normalize artifacts**  
   - Canonical manifest with stable paths and metadata.
   - Record raw artifacts for debugging.
   - Build asset map (images/css/fonts), cover reference.

## Non-goals

- No LLM usage (observations/extractions handled elsewhere).
- No styling or formatting preservation beyond basic structure.
- No “pretty” output for external ebook standards.

## Data model plan (minimal, public repo)

Goal: make this a **standalone, general-purpose** Python module with a small,
stable output surface. It is **not** a server or service — just classes and
pure functions that can be imported by FantasyWorldBible (or any other app).

### Minimal output model (serialization only)

**NormalizedBook**
- `metadata` (title, language, identifiers)
- `chapters[]` (ordered, real chapters only)
- `toc[]` (mirrors chapters; chapter-only TOC)
- `chunks[]` (paragraph chunks, numbered per chapter)
- `artifacts` (raw OPF/NCX/nav + container for debugging)

### Public surface (ebooklib-backed)

- `EbookNormalizer` / `SimpleBook`  
  - Uses `ebooklib` to read EPUBs and produce a serialized dict.
- `serialize(book: SimpleBook) -> dict`

### Serialization schema (minimal)

```json
{
  "metadata": {
    "title": "The Hobbit",
    "language": "en",
    "identifiers": ["urn:uuid:..."]
  },
  "manifest": [
    { "href": "text/part0001.html", "media_type": "application/xhtml+xml", "role": "content" }
  ],
  "spine": ["text/part0001.html", "text/part0002.html"],
  "chapters": [
    { "id": "ch-001", "label": "Chapter I", "href": "text/part0006.html", "text": "..." }
  ],
  "toc": [
    { "label": "Chapter I", "href": "text/part0006.html", "chapter_id": "ch-001" }
  ],
  "chunks": [
    { "id": "ch-001:0001", "chapter_id": "ch-001", "text": "...", "ordinal": 1 }
  ],
  "assets": [
    { "href": "images/cover.jpeg", "media_type": "image/jpeg", "is_cover": true }
  ],
  "artifacts": {
    "container": "META-INF/container.xml",
    "opf": "content.opf",
    "toc_ncx": "toc.ncx",
    "toc_nav": "toc.xhtml"
  }
}
```

### Simplifications vs current flow

- Drop **ImportRun** (tracking belongs to the host app).
- Drop **Chapter** as a first-class entity; represent it via TOC labels + section grouping.
- Drop validation status fields; leave validation to the host app.
- Keep only **sections + chunks** as canonical text units.
- No server/API layer — only Python classes + optional JSON export schema.

### Deterministic derivation rules

- **Sections** are ordered by spine; label from TOC/nav or first heading.
- **Chunks** are generated from section text using deterministic sizing rules.
- No LLM usage; all rules are pure functions on EPUB contents.

## Notes

- Must support OPF 2.0 + 3.0 and NCX/nav TOC.
- Never assume OPF at archive root.

## Chapter detection (deterministic, no LLM)

We want **real chapters**, not every “section” in the EPUB.

### Inputs used
- TOC/nav entries (preferred)
- Spine order (fallback + ordering)
- Heading text from content files (fallback)

### Heuristics (apply in order)
1. **Accept TOC entries that look like chapters**  
   - Labels that match: `Chapter`, `Ch.`, `Book`, `Part`, Roman numerals, or numeric ordinals.
2. **Exclude front/back matter**  
   - Labels like: `Titlepage`, `Cover`, `Copyright`, `Imprint`, `Dedication`, `Preface`,
     `Acknowledgments`, `Notes`, `Endnotes`, `Colophon`, `About the author`, `TOC`, `Contents`.
3. **Fallback to headings in spine**  
   - If TOC is missing or unhelpful, treat first heading in each spine item as candidate.
4. **Normalize labels**  
   - Standardize to `Chapter {N}` when the label is numeric or roman.

### Outputs
- `chapters[]` contains only accepted chapter candidates.
- `toc[]` mirrors `chapters[]` exactly.

## Chunking

- Chunk **paragraphs** in chapter order.
- Each chunk has a **chapter-local ordinal** (`1..N` per chapter).
- Target chunk size is deterministic and configurable (e.g., by char count).
