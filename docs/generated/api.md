# SimpleBook API Reference

## Module: `simplebook`

_Note: import failed, parsed from source (No module named 'ebooklib')._

## Module: `simplebook.main`

_Note: import failed, parsed from source (No module named 'ebooklib')._

### Classes
- `Metadata`
  Minimal book metadata.
- `Node`
  Prototype node to enforce delegation.
- `Chunk`
  Optional grouping of one or more paragraphs.
- `Paragraph`
  A single paragraph taken from the HTML.
- `Chapter`
  No docstring.
- `EbookContent`
  EpubBook extension with spine classification helpers.
- `SimpleBook`
  No docstring.
- `EbookNormalizer`
  Manages conversion of an ebook into a SimpleBook.

### Functions
- `_clean_text`
  No docstring.
- `_ordered_items`
  No docstring.
- `_classify_label_type`
  No docstring.
- `_heading_matches_chapter`
  No docstring.
- `_extract_heading_texts`
  No docstring.
- `_extract_heading_label`
  No docstring.
- `_classify_html_item`
  No docstring.

## Module: `simplebook.cli`

_Note: import failed, parsed from source (No module named 'ebooklib')._

### Functions
- `_parse_args`
  No docstring.
- `_load_schema`
  No docstring.
- `main`
  No docstring.

## Module: `simplebook.schema_validator`

_Note: import failed, parsed from source (No module named 'ebooklib')._

### Functions
- `load_schema`
  Load the JSON schema from file.

  Returns:
      Dictionary containing the JSON schema
    
  Raises:
      FileNotFoundError: If schema file is not found
      json.JSONDecodeError: If schema file is invalid JSON
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
- `assert_valid_output`
  Assert that output is valid, raising an exception if not.

  Useful for testing.

  Args:
      data: The output data to validate
      schema: Optional schema dictionary. If None, loads from file.
    
  Raises:
      AssertionError: If validation fails
      ImportError: If jsonschema library is not installed
- `print_validation_report`
  Print a validation report for a JSON file.

  Args:
      json_path: Path to the JSON file to validate

### Constants
- `SCHEMA_PATH` = `<expr>`

## Module: `simplebook.config`

_Note: import failed, parsed from source (No module named 'ebooklib')._

### Constants
- `MAX_CHUNK_CHARS` = `1200`
- `MAX_CHUNK_ADDITION_CHARS` = `300`
- `MIN_PARAGRAPH_CHARS` = `80`
- `LARGE_PARAGRAPH_CHARS` = `400`
- `CHAPTER_PATTERNS` = `['chapter', 'ch.', 'book', 'part']`
- `ROMAN_NUMERALS` = `['i', 'ii', 'iii', 'iv', 'v', 'vi', 'vii', 'viii', 'ix', 'x', 'xi', 'xii', 'xiii', 'xiv', 'xv', 'xvi', 'xvii', 'xviii', 'xix', 'xx', 'xxi', 'xxii', 'xxiii', 'xxiv', 'xxv', 'xxvi', 'xxvii', 'xxviii', 'xxix', 'xxx', 'xxxi', 'xxxii', 'xxxiii', 'xxxiv', 'xxxv', 'xxxvi', 'xxxvii', 'xxxviii', 'xxxix', 'xl', 'xli', 'xlii', 'xliii', 'xliv', 'xlv', 'xlvi', 'xlvii', 'xlviii', 'xlix', 'l']`
- `FRONT_MATTER_KEYWORDS` = `['titlepage', 'cover', 'copyright', 'imprint', 'dedication', 'preface', 'foreword', 'introduction', 'prologue', 'illustration', 'illustrations']`
- `BACK_MATTER_KEYWORDS` = `['acknowledgments', 'acknowledgements', 'notes', 'endnotes', 'epilogue', 'afterword', 'colophon', 'about the author', 'about']`
- `NON_CHAPTER_KEYWORDS` = `<expr>`
- `OPENING_QUOTES` = `['"', '"', "'", '„']`
- `CLOSING_QUOTES` = `['"', '"', "'", '"']`
- `GUILLEMET_OPEN` = `'<<'`
- `GUILLEMET_CLOSE` = `'>>'`
- `STRIP_ELEMENTS` = `['script', 'style', 'nav']`
- `IMAGE_TYPES` = `['image/jpeg', 'image/png', 'image/gif', 'image/svg+xml']`
- `STYLESHEET_TYPES` = `['text/css']`
- `FONT_TYPES` = `['font/ttf', 'font/otf', 'font/woff', 'font/woff2', 'application/font-woff', 'application/font-woff2', 'application/vnd.ms-opentype', 'application/x-font-ttf', 'application/x-font-otf']`
