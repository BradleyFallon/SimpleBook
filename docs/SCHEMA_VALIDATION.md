# Schema Validation System

The src includes a JSON Schema validation system to ensure the SimpleBook output conforms to the expected format.

## Files

- **`output_schema.json`**: JSON Schema (Draft 7) defining the SimpleBook output format
- **`schema_validator.py`**: Python module for validating output against the schema
- **`test_schema_validator.py`**: Unit tests for the validation system

## Installation

The validation system requires the `jsonschema` library:

```bash
pip install jsonschema
```

## Usage

### Command Line

Validate a JSON file from the command line:

```bash
python schema_validator.py output.json
```

This will print a validation report showing whether the file is valid and any errors found.

### Python API

#### Validate a dictionary

```python
from schema_validator import validate_output

data = {
    "metadata": {...},
    "chapters": [...]
}

is_valid, errors = validate_output(data)

if is_valid:
    print("✅ Output is valid")
else:
    print("❌ Validation errors:")
    for error in errors:
        print(f"  - {error}")
```

#### Validate a JSON file

```python
from schema_validator import validate_output_file

is_valid, errors = validate_output_file("output.json")
```

#### Assert validity (for testing)

```python
from schema_validator import assert_valid_output

# Raises AssertionError if invalid
assert_valid_output(data)
```

#### Print validation report

```python
from schema_validator import print_validation_report

print_validation_report("output.json")
```

## Schema Overview

The output schema defines the SimpleBook tree structure:

### Required Fields

- **`metadata`**: Book metadata (title, author, language, isbn, uuid)
- **`chapters`**: List of chapters with their content

### Chapter Structure

Each chapter contains:
- **`name`**: Chapter title/name (required, non-empty string)
- **`elements`**: Array of typed element objects (paragraphs, blockquotes, tables, etc.)
- **`chunks`**: Array of element indexes where new chunks start

### Chunk Structure

Each chunk entry is:
- **integer**: Zero-based element index where a new chunk starts

### Element Fields

Each element includes:
- **`type`**: Element type (e.g., paragraph, blockquote, table)
- **`text`**: Normalized text (optional)
- **`rows`**: Table rows (for table elements)
- **`raw_html`**: Original HTML snippet (optional)
- **`markdown`**: Markdown representation (optional)
- **`role`**: Semantic role (optional; title/body/comment/heading)

## Example Valid Output

```json
{
  "metadata": {
    "title": "Example Book",
    "author": "Jane Doe",
    "language": "en",
    "isbn": "1234567890",
    "uuid": "abc-def-123"
  },
  "chapters": [
    {
      "name": "Chapter 1",
      "elements": [
        {
          "type": "heading",
          "text": "Chapter 1",
          "role": "title",
          "markdown": "# Chapter 1",
          "raw_html": "<h1>Chapter 1</h1>"
        },
        {
          "type": "paragraph",
          "text": "This is the first paragraph.",
          "role": "body",
          "markdown": "This is the first paragraph.",
          "raw_html": "<p>This is the first paragraph.</p>"
        }
      ],
      "chunks": [0]
    },
    {
      "name": "Chapter 2",
      "elements": [
        { "type": "paragraph", "text": "Chapter two content here." }
      ],
      "chunks": [0]
    }
  ]
}
```

## Integration with Tests

The validation system can be integrated into your test suite:

```python
def test_normalizer_output_schema_compliance():
    """Test that normalizer output conforms to schema."""
    from simplebook import SimpleBook
    from schema_validator import assert_valid_output
    
    book = SimpleBook()
    book.load_epub("test.epub")
    output = book.serialize()
    
    # Will raise AssertionError if invalid
    assert_valid_output(output)
```

## Common Validation Errors

### Missing Required Field

```
metadata: 'language' is a required property
```

**Fix**: Ensure all required fields are present in the output.

### Missing Chapter Fields

```
chapters.0: 'elements' is a required property
```

**Fix**: Ensure each chapter has name, elements, and chunks fields.

### Wrong Type

```
chapters: 'string' is not of type 'array'
```

**Fix**: Ensure fields have the correct type (e.g., chapters should be an array).

### Invalid Ordinal

```
chapters.0.chunks.0: 'x' is not of type 'integer'
```

**Fix**: Chunk entries must be integers (element indexes).

## Extending the Schema

To modify the schema:

1. Edit `output_schema.json`
2. Update the validation tests in `test_schema_validator.py`
3. Run tests to ensure changes don't break existing functionality
4. Update this documentation

## Testing

Run the validation system tests:

```bash
pytest test_schema_validator.py -v
```

Or use the simple test script (no pytest required):

```bash
python test_schema_simple.py
```

All tests should pass if `jsonschema` is installed.
