# Testing Guide

This document explains how to test the src with real EPUB files.

## Test Structure

```
src/
├── tests/epubs/          # Input EPUB files
├── tests/      # Expected JSON outputs
├── test_golden_files.py # Golden file test suite
└── TESTING.md          # This file
```

## Quick Start

### 1. Add Test EPUBs

Download public domain EPUBs and place them in `tests/epubs/`:

```bash
cd tests/epubs

# Example: Download from Project Gutenberg
wget https://www.gutenberg.org/ebooks/84.epub.noimages -O frankenstein.epub
wget https://www.gutenberg.org/ebooks/35.epub.noimages -O time_machine.epub
wget https://www.gutenberg.org/ebooks/62.epub.noimages -O princess_of_mars.epub
```

See `tests/epubs/README.md` for more sources.

### 2. Generate Golden Files

Generate expected outputs for all test EPUBs:

```bash
python test_golden_files.py --generate
```

This will:
- Process each EPUB in `tests/epubs/`
- Generate normalized JSON output
- Validate output against schema
- Save golden files to `tests/`

### 3. Run Tests

Run the golden file tests:

```bash
pytest test_golden_files.py -v
```

This will:
- Compare normalizer output against golden files
- Validate schema compliance
- Test deterministic output (same input → same output)

## Test Types

### Golden File Tests

Compare normalizer output against pre-generated expected outputs:

```bash
pytest test_golden_files.py::TestGoldenFiles::test_golden_file_match -v
```

### Schema Compliance Tests

Validate that output conforms to the JSON schema:

```bash
pytest test_golden_files.py::TestGoldenFiles::test_output_schema_compliance -v
```

### Determinism Tests

Verify that processing the same EPUB twice produces identical output:

```bash
pytest test_golden_files.py::TestGoldenFiles::test_deterministic_output -v
```

## Updating Golden Files

### Update All Golden Files

When you intentionally change the normalizer's output format:

```bash
python test_golden_files.py --generate
```

⚠️ **Warning**: Only do this if you're confident the new output is correct!

### Update a Specific Golden File

Update just one golden file:

```bash
python test_golden_files.py --update frankenstein.epub
```

## Recommended Test EPUBs

For comprehensive testing, include:

1. **EPUB 2.0 books** (with NCX navigation)
2. **EPUB 3.0 books** (with nav document)
3. **Various structures**:
   - Simple linear novels
   - Books with parts/sections
   - Books with front matter (preface, dedication)
   - Books with back matter (appendices, notes)
   - Books with unusual formatting

## Troubleshooting

### No EPUBs Found

```
❌ No EPUB files found in tests/epubs
```

**Solution**: Add EPUB files to the `tests/epubs/` directory.

### No Golden File

```
SKIPPED - No golden file for frankenstein.epub
```

**Solution**: Generate golden files with `python test_golden_files.py --generate`

### Output Differs from Golden File

```
AssertionError: Output differs from golden file for frankenstein.epub
```

**Possible causes**:
1. You changed the normalizer code (expected)
2. There's a bug in the normalizer (investigate)
3. The golden file is outdated (regenerate if intentional)

**Solution**: 
- If the change is intentional: `python test_golden_files.py --update frankenstein.epub`
- If it's a bug: Fix the normalizer code

### Schema Validation Fails

```
Output for frankenstein.epub does not conform to schema
```

**Solution**: Fix the normalizer to produce valid output, or update the schema if needed.

## CI/CD Integration

Add to your CI pipeline:

```yaml
# .github/workflows/test.yml
- name: Run golden file tests
  run: |
    pytest test_golden_files.py -v
```

## Best Practices

1. **Version control golden files**: Commit them to git so changes are tracked
2. **Review golden file changes**: When regenerating, review the diff carefully
3. **Test with diverse EPUBs**: Include various formats and structures
4. **Keep EPUBs small**: Use shorter books for faster tests
5. **Document test cases**: Note why each EPUB was chosen

## Example Workflow

```bash
# 1. Add a new test EPUB
cp ~/Downloads/new_book.epub tests/epubs/

# 2. Generate its golden file
python test_golden_files.py --update new_book.epub

# 3. Run all tests
pytest test_golden_files.py -v

# 4. Commit if everything passes
git add tests/epubs/new_book.epub tests/new_book.json
git commit -m "Add test case: new_book.epub"
```
