"""
Simple test script for schema validation (no pytest required).
Run with: python3 test_schema_simple.py
"""

import json

try:
    import pytest
    PYTEST_AVAILABLE = True
except ImportError:
    PYTEST_AVAILABLE = False
    pytest = None

# Check if jsonschema is available
try:
    from simplebook.schema_validator import validate_output, load_schema
    print("✅ schema_validator module loaded successfully")
    JSONSCHEMA_AVAILABLE = True
except ImportError as e:
    print(f"⚠️  jsonschema library not available: {e}")
    print("   Install with: pip3 install --user jsonschema")
    JSONSCHEMA_AVAILABLE = False


def _run_load_schema():
    """Test loading the schema file."""
    print("\n📋 Test: Load schema file")
    try:
        schema = load_schema()
        assert isinstance(schema, dict)
        assert "$schema" in schema
        assert "properties" in schema
        print("   ✅ Schema loaded successfully")
        print(f"   - Schema has {len(schema.get('properties', {}))} top-level properties")
        print(f"   - Required fields: {', '.join(schema.get('required', []))}")
        return True
    except Exception as e:
        print(f"   ❌ Failed: {e}")
        return False


def _run_validate_minimal_output():
    """Test validation of minimal valid output."""
    print("\n📋 Test: Validate minimal valid output")
    
    if not JSONSCHEMA_AVAILABLE:
        print("   ⏭️  Skipped (jsonschema not available)")
        return None
    
    try:
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
        
        if is_valid:
            print("   ✅ Minimal output is valid")
            return True
        else:
            print(f"   ❌ Validation failed with {len(errors)} errors:")
            for error in errors:
                print(f"      - {error}")
            return False
    except Exception as e:
        print(f"   ❌ Failed: {e}")
        return False


def _run_validate_complete_output():
    """Test validation of complete valid output."""
    print("\n📋 Test: Validate complete valid output")
    
    if not JSONSCHEMA_AVAILABLE:
        print("   ⏭️  Skipped (jsonschema not available)")
        return None
    
    try:
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
        
        if is_valid:
            print("   ✅ Complete output is valid")
            return True
        else:
            print(f"   ❌ Validation failed with {len(errors)} errors:")
            for error in errors:
                print(f"      - {error}")
            return False
    except Exception as e:
        print(f"   ❌ Failed: {e}")
        return False


def _run_validate_invalid_output():
    """Test that invalid output is correctly rejected."""
    print("\n📋 Test: Detect invalid output")
    
    if not JSONSCHEMA_AVAILABLE:
        print("   ⏭️  Skipped (jsonschema not available)")
        return None
    
    try:
        # Missing required field 'language'
        data = {
            "metadata": {
                "title": "Test Book",
                "author": "Test Author"
                # Missing 'language'
            },
            "chapters": []
        }
        
        is_valid, errors = validate_output(data)
        
        if not is_valid and len(errors) > 0:
            print(f"   ✅ Invalid output correctly rejected ({len(errors)} errors found)")
            print(f"      Example error: {errors[0]}")
            return True
        else:
            print("   ❌ Invalid output was not rejected")
            return False
    except Exception as e:
        print(f"   ❌ Failed: {e}")
        return False


def test_load_schema():
    if not JSONSCHEMA_AVAILABLE:
        if PYTEST_AVAILABLE:
            pytest.skip("jsonschema not available")
        return
    assert _run_load_schema() is True


def test_validate_minimal_output():
    result = _run_validate_minimal_output()
    if result is None:
        if PYTEST_AVAILABLE:
            pytest.skip("jsonschema not available")
        return
    assert result is True


def test_validate_complete_output():
    result = _run_validate_complete_output()
    if result is None:
        if PYTEST_AVAILABLE:
            pytest.skip("jsonschema not available")
        return
    assert result is True


def test_validate_invalid_output():
    result = _run_validate_invalid_output()
    if result is None:
        if PYTEST_AVAILABLE:
            pytest.skip("jsonschema not available")
        return
    assert result is True


def main():
    """Run all tests."""
    print("=" * 60)
    print("Schema Validation System Tests")
    print("=" * 60)
    
    results = []
    
    # Test 1: Load schema
    results.append(_run_load_schema())
    
    # Test 2: Validate minimal output
    results.append(_run_validate_minimal_output())
    
    # Test 3: Validate complete output
    results.append(_run_validate_complete_output())
    
    # Test 4: Detect invalid output
    results.append(_run_validate_invalid_output())
    
    # Summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    
    passed = sum(1 for r in results if r is True)
    failed = sum(1 for r in results if r is False)
    skipped = sum(1 for r in results if r is None)
    total = len(results)
    
    print(f"Total:   {total}")
    print(f"Passed:  {passed} ✅")
    print(f"Failed:  {failed} ❌")
    print(f"Skipped: {skipped} ⏭️")
    
    if not JSONSCHEMA_AVAILABLE:
        print("\n⚠️  Note: Some tests were skipped because jsonschema is not installed.")
        print("   Install with: pip3 install --user jsonschema")
    
    print("=" * 60)
    
    return failed == 0


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
