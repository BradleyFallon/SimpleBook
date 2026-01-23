"""
Check if all required dependencies are installed.
"""

import sys

def check_module(name, package_name=None):
    """Check if a module is available."""
    if package_name is None:
        package_name = name
    
    try:
        __import__(name)
        print(f"✅ {package_name}")
        return True
    except ImportError:
        print(f"❌ {package_name} - Install with: pip3 install --user {package_name}")
        return False

def main():
    print("=" * 60)
    print("Checking SimpleBook dependencies...")
    print("=" * 60)
    
    print("\n📦 Core Dependencies:")
    core_ok = True
    core_ok &= check_module("ebooklib")
    core_ok &= check_module("bs4", "beautifulsoup4")
    core_ok &= check_module("lxml")
    
    print("\n🧪 Testing Dependencies:")
    test_ok = True
    test_ok &= check_module("pytest")
    test_ok &= check_module("hypothesis")
    
    print("\n📋 Schema Validation:")
    schema_ok = check_module("jsonschema")
    
    print("\n" + "=" * 60)
    
    if core_ok and test_ok and schema_ok:
        print("✅ All dependencies installed!")
        print("\nYou can now:")
        print("  - Generate golden files: python3 test_golden_files.py --generate")
        print("  - Run tests: pytest test_golden_files.py -v")
    else:
        print("⚠️  Some dependencies are missing.")
        print("\nQuick install:")
        print("  pip3 install --user -r requirements.txt")
        print("\nOr install individually:")
        if not core_ok:
            print("  pip3 install --user ebooklib beautifulsoup4 lxml")
        if not test_ok:
            print("  pip3 install --user pytest hypothesis")
        if not schema_ok:
            print("  pip3 install --user jsonschema")
    
    print("=" * 60)
    
    return 0 if (core_ok and test_ok and schema_ok) else 1

if __name__ == "__main__":
    sys.exit(main())
