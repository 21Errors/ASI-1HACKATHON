#!/usr/bin/env python
"""Test the DocumentParser module"""

import sys
import asyncio

# Test imports
try:
    from backend.doc_parser import DocumentParser
    print("✓ DocumentParser imported successfully")
except ImportError as e:
    print(f"✗ Import error: {e}")
    sys.exit(1)

# Test instantiation
try:
    parser = DocumentParser()
    print("✓ DocumentParser instantiated successfully")
except Exception as e:
    print(f"✗ Instantiation error: {e}")
    sys.exit(1)

# Test fallback response
try:
    fallback = parser._create_fallback_response()
    assert "person_or_company" in fallback
    assert "services" in fallback
    assert isinstance(fallback["services"], list)
    print("✓ Fallback response works correctly")
    print(f"  - person_or_company: {fallback['person_or_company']}")
    print(f"  - services count: {len(fallback['services'])}")
except Exception as e:
    print(f"✗ Fallback response error: {e}")
    sys.exit(1)

# Test extract_text with invalid path (should fail gracefully)
try:
    text = parser.extract_text("/nonexistent/file.pdf", ".pdf")
    print(f"✗ Should have raised error for nonexistent file")
except Exception as e:
    print(f"✓ Correctly handles missing files: {type(e).__name__}")

print("\n✓ All basic tests passed!")
