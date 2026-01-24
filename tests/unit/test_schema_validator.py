"""
Unit tests for schema validation.
Tests that the validator correctly identifies valid and invalid output.
"""

import json
import tempfile
from pathlib import Path
import pytest

try:
    from simplebook.schema_validator import (
        load_schema,
        validate_output,
        validate_output_file,
        assert_valid_output,
        JSONSCHEMA_AVAILABLE
    )
    SKIP_TESTS = not JSONSCHEMA_AVAILABLE
    SKIP_REASON = "jsonschema library not installed"
except ImportError:
    SKIP_TESTS = True
    SKIP_REASON = "schema_validator module not available"


@pytest.mark.skipif(SKIP_TESTS, reason=SKIP_REASON)
class TestSchemaValidator:
    """Test schema validation functionality."""
    
    def test_load_schema(self):
        """Test loading the schema file."""
        schema = load_schema()
        
        assert isinstance(schema, dict)
        assert "$schema" in schema
        assert "properties" in schema
        assert "required" in schema
    
    def test_validate_minimal_valid_output(self):
        """Test validation of minimal valid output."""
        data = {
            "metadata": {
                "title": "Test Book",
                "author": "Test Author",
                "language": "en",
                "isbn": "",
                "uuid": ""
            },
            "chapters": []
        }
        
        is_valid, errors = validate_output(data)
        
        assert is_valid, f"Validation failed: {errors}"
        assert len(errors) == 0
    
    def test_validate_complete_valid_output(self):
        """Test validation of complete valid output."""
        data = {
            "metadata": {
                "title": "Complete Book",
                "author": "Jane Doe",
                "language": "en-US",
                "isbn": "123456789",
                "uuid": "abc-def-123"
            },
            "chapters": [
                {
                    "name": "Chapter 1",
                    "elements": [
                        {"type": "paragraph", "text": "This is chapter one content."},
                        {"type": "paragraph", "text": "It has multiple sentences."}
                    ],
                    "chunks": [0]
                }
            ]
        }
        
        is_valid, errors = validate_output(data)
        
        assert is_valid, f"Validation failed: {errors}"
        assert len(errors) == 0
    
    def test_validate_missing_required_field(self):
        """Test validation fails when required field is missing."""
        data = {
            "metadata": {
                "title": "Test Book",
                "author": "Test Author"
                # Missing 'language'
            },
            "chapters": []
        }
        
        is_valid, errors = validate_output(data)
        
        assert not is_valid
        assert len(errors) > 0
        assert any("language" in e for e in errors)
    
    def test_validate_invalid_chapter_structure(self):
        """Test validation fails for invalid chapter structure."""
        data = {
            "metadata": {
                "title": "Test Book",
                "author": "Test Author",
                "language": "en"
            },
            "chapters": [
                {
                    "name": "Chapter 1"
                    # Missing 'elements' and 'chunks'
                }
            ]
        }
        
        is_valid, errors = validate_output(data)
        
        assert not is_valid
        assert len(errors) > 0
    
    def test_validate_invalid_ordinal(self):
        """Test validation fails for invalid chunk ordinal."""
        data = {
            "metadata": {
                "title": "Test Book",
                "author": "Test Author",
                "language": "en"
            },
            "chapters": [
                {
                    "name": "Chapter 1",
                    "elements": [{"type": "paragraph", "text": "Content"}],
                    "chunks": ["not-an-int"]
                }
            ]
        }
        
        is_valid, errors = validate_output(data)
        
        assert not is_valid
        assert len(errors) > 0
        assert any("integer" in e.lower() for e in errors)
    
    def test_validate_wrong_type(self):
        """Test validation fails when field has wrong type."""
        data = {
            "metadata": {
                "title": "Test Book",
                "author": "Test Author",
                "language": "en"
            },
            "chapters": "not-an-array"  # Should be array
        }
        
        is_valid, errors = validate_output(data)
        
        assert not is_valid
        assert len(errors) > 0
        assert any("array" in e.lower() for e in errors)
    
    def test_assert_valid_output_passes(self):
        """Test assert_valid_output doesn't raise for valid data."""
        data = {
            "metadata": {
                "title": "Test Book",
                "author": "Test Author",
                "language": "en"
            },
            "chapters": []
        }
        
        # Should not raise
        assert_valid_output(data)
    
    def test_assert_valid_output_raises(self):
        """Test assert_valid_output raises for invalid data."""
        data = {
            "metadata": {
                "title": "Test Book"
                # Missing required fields
            }
        }
        
        with pytest.raises(AssertionError, match="validation failed"):
            assert_valid_output(data)
    
    def test_validate_output_file(self, tmp_path):
        """Test validating a JSON file."""
        # Create a valid JSON file
        data = {
            "metadata": {
                "title": "Test Book",
                "author": "Test Author",
                "language": "en"
            },
            "chapters": []
        }
        
        json_file = tmp_path / "output.json"
        json_file.write_text(json.dumps(data, indent=2))
        
        is_valid, errors = validate_output_file(json_file)
        
        assert is_valid
        assert len(errors) == 0
    
    def test_validate_output_file_not_found(self):
        """Test validation fails for non-existent file."""
        with pytest.raises(FileNotFoundError):
            validate_output_file("nonexistent.json")
    
    def test_validate_output_file_invalid_json(self, tmp_path):
        """Test validation fails for invalid JSON."""
        json_file = tmp_path / "invalid.json"
        json_file.write_text("{ this is not valid JSON }")
        
        with pytest.raises(json.JSONDecodeError):
            validate_output_file(json_file)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
