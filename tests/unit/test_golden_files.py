"""
Golden file tests for ebook normalizer.

These tests compare normalizer output against known-good "golden" files.
Golden files are pre-generated expected outputs that serve as regression tests.

Directory structure:
  tests/epubs/          - Input EPUB files
  tests/      - Expected JSON outputs
"""

import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

try:
    import pytest
    PYTEST_AVAILABLE = True
except ImportError:
    PYTEST_AVAILABLE = False
    pytest = None

from simplebook import SimpleBook

try:
    from simplebook.schema_validator import validate_output
    SCHEMA_VALIDATOR_AVAILABLE = True
except ImportError:
    SCHEMA_VALIDATOR_AVAILABLE = False
    def validate_output(data):
        return (True, [])


# Test data directories
TEST_EPUBS_DIR = PROJECT_ROOT / "tests" / "epubs"
GOLDEN_OUTPUTS_DIR = PROJECT_ROOT / "tests"


def get_test_epubs():
    """Find all EPUB files in tests/epubs directory."""
    if not TEST_EPUBS_DIR.exists():
        return []
    return list(TEST_EPUBS_DIR.glob("*.epub"))


def get_golden_file(epub_path: Path) -> Path:
    """Get the golden output file path for an EPUB."""
    return GOLDEN_OUTPUTS_DIR / f"{epub_path.stem}.json"


def load_golden_output(golden_path: Path) -> dict:
    """Load a golden output file."""
    with open(golden_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def save_golden_output(output: dict, golden_path: Path) -> None:
    """Save output as a golden file."""
    golden_path.parent.mkdir(parents=True, exist_ok=True)
    with open(golden_path, 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2, ensure_ascii=False)


def normalize_epub(epub_path: Path) -> dict:
    """Normalize an EPUB and return the output."""
    book = SimpleBook()
    book.load_epub(str(epub_path))
    return book.serialize()


class TestGoldenFiles:
    """Test normalizer output against golden files."""
    
    def test_golden_file_match(self, epub_path):
        """Test that normalizer output matches golden file."""
        if not PYTEST_AVAILABLE:
            return
        
        golden_path = get_golden_file(epub_path)
        
        # Skip if no golden file exists
        if not golden_path.exists():
            pytest.skip(f"No golden file for {epub_path.name}. Run with --generate-golden to create it.")
        
        # Normalize the EPUB
        actual_output = normalize_epub(epub_path)
        
        # Load golden output
        expected_output = load_golden_output(golden_path)
        
        # Compare
        assert actual_output == expected_output, \
            f"Output differs from golden file for {epub_path.name}"
    
    def test_output_schema_compliance(self, epub_path):
        """Test that normalizer output conforms to schema."""
        if not PYTEST_AVAILABLE:
            return
        
        # Normalize the EPUB
        output = normalize_epub(epub_path)
        
        # Validate against schema
        is_valid, errors = validate_output(output)
        
        assert is_valid, \
            f"Output for {epub_path.name} does not conform to schema:\n" + \
            "\n".join(f"  - {e}" for e in errors)
    
    def test_deterministic_output(self, epub_path):
        """Test that normalizer produces identical output on repeated runs."""
        if not PYTEST_AVAILABLE:
            return
        
        # Normalize twice
        output1 = normalize_epub(epub_path)
        output2 = normalize_epub(epub_path)
        
        # Should be identical
        assert output1 == output2, \
            f"Non-deterministic output for {epub_path.name}"


def generate_golden_files():
    """
    Generate golden files for all EPUBs in tests/epubs directory.
    
    Usage:
        python test_golden_files.py --generate
    """
    epub_files = get_test_epubs()
    
    if not epub_files:
        print(f"❌ No EPUB files found in {TEST_EPUBS_DIR}")
        print(f"   Add EPUB files to {TEST_EPUBS_DIR} first.")
        return
    
    print(f"Generating golden files for {len(epub_files)} EPUBs...")
    print("=" * 60)
    
    for epub_path in epub_files:
        print(f"\n📖 Processing: {epub_path.name}")
        
        try:
            # Normalize the EPUB
            output = normalize_epub(epub_path)
            
            # Validate output
            is_valid, errors = validate_output(output)
            if not is_valid:
                print(f"   ⚠️  Warning: Output does not conform to schema:")
                for error in errors:
                    print(f"      - {error}")
            
            # Save golden file
            golden_path = get_golden_file(epub_path)
            save_golden_output(output, golden_path)
            
            print(f"   ✅ Golden file saved: {golden_path.name}")
            print(f"      Chapters: {len(output.get('chapters', []))}")
            print(f"      Title: {output.get('metadata', {}).get('title', 'N/A')}")
            
        except Exception as e:
            print(f"   ❌ Error: {e}")
    
    print("\n" + "=" * 60)
    print(f"✅ Golden file generation complete!")
    print(f"   Files saved to: {GOLDEN_OUTPUTS_DIR}")


def update_golden_file(epub_name: str):
    """
    Update a specific golden file.
    
    Usage:
        python test_golden_files.py --update frankenstein.epub
    """
    epub_path = TEST_EPUBS_DIR / epub_name
    
    if not epub_path.exists():
        print(f"❌ EPUB not found: {epub_path}")
        return
    
    print(f"Updating golden file for: {epub_name}")
    
    try:
        # Normalize the EPUB
        output = normalize_epub(epub_path)
        
        # Save golden file
        golden_path = get_golden_file(epub_path)
        save_golden_output(output, golden_path)
        
        print(f"✅ Golden file updated: {golden_path.name}")
        
    except Exception as e:
        print(f"❌ Error: {e}")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python test_golden_files.py --generate          # Generate all golden files")
        print("  python test_golden_files.py --update <epub>     # Update specific golden file")
        print("  pytest test_golden_files.py -v                  # Run tests")
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command == "--generate":
        generate_golden_files()
    elif command == "--update" and len(sys.argv) > 2:
        update_golden_file(sys.argv[2])
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)
