# SimpleBook API Reference

## Module: `simplebook`

## Module: `simplebook.main`

### Classes
- `Chapter`
  Chapter container with elements and chunk boundaries.
- `Chunk`
  Logical grouping of elements within a chapter.
- `EbookContent`
  EpubBook extension with spine classification helpers.
- `EbookNormalizer`
  Manages conversion of an ebook into a SimpleBook.
- `Element`
  Typed content element extracted from HTML.
- `Metadata`
  Minimal book metadata.
- `Node`
  Prototype node to enforce delegation.
- `SimpleBook`
  Top-level model containing metadata and chapters.

### Functions
- `_assert_supported_text`
  Raise if text appears outside the supported tag set.
- `_blockquote_text`
  Extract blockquote text, excluding nested cite content.
- `_classify_html_item`
  Classify an HTML spine item as chapter/front/back/other.
- `_classify_label_type`
  Classify a label as chapter/front/back/other by heuristics.
- `_clean_text`
  Normalize whitespace, quotes, and ASCII in a raw text string.
- `_extract_elements`
  Extract typed Elements from HTML soup in document order.
- `_extract_heading_label`
  Combine heading fragments into a single chapter label.
- `_extract_heading_texts`
  Collect heading-like text nodes used to name a chapter.
- `_heading_matches_chapter`
  Return True if heading text looks like a chapter label.
- `_html_to_soup`
  Parse HTML into BeautifulSoup and remove stripped elements.
- `_manual_text_from_html`
  Convert inline emphasis tags to markers and normalize text.
- `_normalize_quotes`
  Normalize straight/curly double quotes to << >> pairs.
- `_ordered_items`
  Return spine-ordered document items from an EbookLib book.
- `_render_markdown`
  Render a lightweight Markdown representation for an element.
- `_table_rows`
  Extract table rows as a list of cleaned cell strings.
- `_to_ascii`
  Transliterate text to ASCII and normalize dashes.

### Constants
- `ALLOWED_TEXT_TAGS` = `{'h4', 'dd', 'blockquote', 'dt', 'th', 'td', 'li', 'h5', 'h2', 'h1', 'cite', 'table', 'p', 'caption', 'h6', 'figcaption', 'h3'}`
- `BACK_MATTER_KEYWORDS` = `['acknowledgments', 'acknowledgements', 'notes', 'endnotes', 'epilogue', 'afterword', 'colophon', 'about the author', 'about']`
- `CHAPTER_PATTERNS` = `['chapter', 'ch.', 'book', 'part']`
- `CHUNK_BP_L` = `200`
- `CHUNK_BP_M` = `100`
- `CHUNK_BP_S` = `50`
- `CHUNK_BP_XL` = `300`
- `CLOSING_QUOTES` = `['"', '"', "'", '"']`
- `CONTAINER_TAGS` = `{'tr', 'tfoot', 'figure', 'div', 'main', 'aside', 'header', 'tbody', 'footer', 'thead', 'ul', 'article', 'dl', 'section', 'ol'}`
- `DOUBLE_QUOTE_CHARS` = `{'„', '“', '”', '"'}`
- `ELEMENT_TAG_TYPES` = `{'p': 'paragraph', 'blockquote': 'blockquote', 'li': 'list_item', 'dt': 'definition_term', 'dd': 'definition_desc', 'cite': 'cite', 'figcaption': 'caption', 'caption': 'caption', 'table': 'table'}`
- `ELEM_BP_L` = `100`
- `ELEM_BP_M` = `30`
- `ELEM_BP_S` = `10`
- `ELEM_BP_XL` = `250`
- `FRONT_MATTER_KEYWORDS` = `['titlepage', 'cover', 'copyright', 'imprint', 'dedication', 'preface', 'foreword', 'introduction', 'prologue', 'illustration', 'illustrations']`
- `GUILLEMET_CLOSE` = `'>>'`
- `GUILLEMET_OPEN` = `'<<'`
- `HEADING_TAGS` = `{'h4', 'h1', 'h6', 'h3', 'h5', 'h2'}`
- `LARGE_PARAGRAPH_WORDS` = `120`
- `MAX_CHUNK_ADDITION_WORDS` = `80`
- `NON_CHAPTER_KEYWORDS` = `['titlepage', 'cover', 'copyright', 'imprint', 'dedication', 'preface', 'foreword', 'introduction', 'prologue', 'illustration', 'illustrations', 'acknowledgments', 'acknowledgements', 'notes', 'endnotes', 'epilogue', 'afterword', 'colophon', 'about the author', 'about', 'toc', 'contents']`
- `OPENING_QUOTES` = `['"', '"', "'", '„']`
- `ROMAN_NUMERALS` = `['i', 'ii', 'iii', 'iv', 'v', 'vi', 'vii', 'viii', 'ix', 'x', 'xi', 'xii', 'xiii', 'xiv', 'xv', 'xvi', 'xvii', 'xviii', 'xix', 'xx', 'xxi', 'xxii', 'xxiii', 'xxiv', 'xxv', 'xxvi', 'xxvii', 'xxviii', 'xxix', 'xxx', 'xxxi', 'xxxii', 'xxxiii', 'xxxiv', 'xxxv', 'xxxvi', 'xxxvii', 'xxxviii', 'xxxix', 'xl', 'xli', 'xlii', 'xliii', 'xliv', 'xlv', 'xlvi', 'xlvii', 'xlviii', 'xlix', 'l']`
- `SOFT_MAX_CHUNK_WORDS` = `300`
- `SOFT_WORD_MAX` = `500`
- `SOFT_WORD_THRESHOLD` = `10`
- `STRIP_ELEMENTS` = `['script', 'style', 'nav']`
- `TABLE_CELL_TAGS` = `{'th', 'td'}`

## Module: `simplebook.cli`

### Functions
- `_load_schema`
  Load a JSON schema from the provided path or the bundled schema.
- `_parse_args`
  Parse CLI arguments for the simplebook command.
- `main`
  Entry point for the simplebook CLI.

## Module: `simplebook.schema_validator`

### Functions
- `assert_valid_output`
  Assert that output is valid, raising an exception if not.

  Useful for testing.

  Args:
      data: The output data to validate
      schema: Optional schema dictionary. If None, loads from file.
    
  Raises:
      AssertionError: If validation fails
      ImportError: If jsonschema library is not installed
- `load_schema`
  Load the JSON schema from file.

  Returns:
      Dictionary containing the JSON schema
    
  Raises:
      FileNotFoundError: If schema file is not found
      json.JSONDecodeError: If schema file is invalid JSON
- `print_validation_report`
  Print a validation report for a JSON file.

  Args:
      json_path: Path to the JSON file to validate
- `validate_output`
  Validate normalized book output against the schema.

  Args:
      data: The output data to validate (as a dictionary)
      schema: Optional schema dictionary. If None, loads from file.
    
  Returns:
      Tuple of (is_valid, errors) where:
      - is_valid: True if validation passes, False otherwise
      - errors: List of validation error messages (empty if valid)
    
  Raises:
      ImportError: If jsonschema library is not installed
- `validate_output_file`
  Validate a JSON file against the schema.

  Args:
      json_path: Path to the JSON file to validate
      schema: Optional schema dictionary. If None, loads from file.
    
  Returns:
      Tuple of (is_valid, errors) where:
      - is_valid: True if validation passes, False otherwise
      - errors: List of validation error messages (empty if valid)
    
  Raises:
      FileNotFoundError: If JSON file is not found
      json.JSONDecodeError: If JSON file is invalid
      ImportError: If jsonschema library is not installed

### Constants
- `JSONSCHEMA_AVAILABLE` = `True`
- `SCHEMA_PATH` = `PosixPath('/Users/fallbro/code/SimpleBook/src/simplebook/output_schema.json')`

## Module: `simplebook.config`
