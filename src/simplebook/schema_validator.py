"""
Schema validation utility for SimpleBook output.

This module provides functions to validate JSON output against the
SimpleBook output schema.
"""

import json
from pathlib import Path
from typing import Any

try:
    import jsonschema
    from jsonschema import validate, ValidationError, Draft7Validator
    JSONSCHEMA_AVAILABLE = True
except ImportError:
    JSONSCHEMA_AVAILABLE = False
    ValidationError = Exception  # type: ignore


# Path to the schema file
SCHEMA_PATH = Path(__file__).parent / "output_schema.json"


def load_schema() -> dict[str, Any]:
    """
    Load the JSON schema from file.
    
    Returns:
        Dictionary containing the JSON schema
        
    Raises:
        FileNotFoundError: If schema file is not found
        json.JSONDecodeError: If schema file is invalid JSON
    """
    if not SCHEMA_PATH.exists():
        raise FileNotFoundError(f"Schema file not found: {SCHEMA_PATH}")
    
    with open(SCHEMA_PATH, 'r', encoding='utf-8') as f:
        return json.load(f)


def validate_output(data: dict[str, Any], schema: dict[str, Any] | None = None) -> tuple[bool, list[str]]:
    """
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
    """
    if not JSONSCHEMA_AVAILABLE:
        raise ImportError(
            "jsonschema library is required for validation. "
            "Install it with: pip install jsonschema"
        )
    
    # Load schema if not provided
    if schema is None:
        schema = load_schema()
    
    # Validate
    validator = Draft7Validator(schema)
    errors = []
    
    for error in validator.iter_errors(data):
        # Format error message with path
        path = ".".join(str(p) for p in error.path) if error.path else "root"
        errors.append(f"{path}: {error.message}")
    
    return (len(errors) == 0, errors)


def validate_output_file(json_path: str | Path, schema: dict[str, Any] | None = None) -> tuple[bool, list[str]]:
    """
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
    """
    json_path = Path(json_path)
    
    if not json_path.exists():
        raise FileNotFoundError(f"JSON file not found: {json_path}")
    
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    return validate_output(data, schema)


def assert_valid_output(data: dict[str, Any], schema: dict[str, Any] | None = None) -> None:
    """
    Assert that output is valid, raising an exception if not.
    
    Useful for testing.
    
    Args:
        data: The output data to validate
        schema: Optional schema dictionary. If None, loads from file.
        
    Raises:
        AssertionError: If validation fails
        ImportError: If jsonschema library is not installed
    """
    is_valid, errors = validate_output(data, schema)
    
    if not is_valid:
        error_msg = "Output validation failed:\n" + "\n".join(f"  - {e}" for e in errors)
        raise AssertionError(error_msg)


def print_validation_report(json_path: str | Path) -> None:
    """
    Print a validation report for a JSON file.
    
    Args:
        json_path: Path to the JSON file to validate
    """
    try:
        is_valid, errors = validate_output_file(json_path)
        
        print(f"Validation Report for: {json_path}")
        print("=" * 60)
        
        if is_valid:
            print("✅ VALID - Output conforms to schema")
        else:
            print("❌ INVALID - Found validation errors:")
            print()
            for i, error in enumerate(errors, 1):
                print(f"{i}. {error}")
        
        print("=" * 60)
        
    except FileNotFoundError as e:
        print(f"❌ ERROR: {e}")
    except json.JSONDecodeError as e:
        print(f"❌ ERROR: Invalid JSON - {e}")
    except ImportError as e:
        print(f"❌ ERROR: {e}")


# CLI interface
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python schema_validator.py <json_file>")
        print()
        print("Validates a JSON file against the SimpleBook output schema.")
        sys.exit(1)
    
    json_file = sys.argv[1]
    print_validation_report(json_file)
