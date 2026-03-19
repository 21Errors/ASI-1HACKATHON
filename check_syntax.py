#!/usr/bin/env python
"""Quick syntax check for document parser"""

import sys

checks = [
    ("backend.doc_parser", "DocumentParser"),
    ("backend.config", "ASI1_API_KEY"),
    ("main", "app"),
    ("main", "DocumentAnalysisRequest"),
    ("main", "doc_parser"),
]

print("Checking Python syntax and imports...")
print("-" * 50)

all_good = True
for module, item in checks:
    try:
        mod = __import__(module, fromlist=[item])
        obj = getattr(mod, item, None)
        if obj is not None:
            print(f"✓ {module}.{item}")
        else:
            print(f"✗ {module}.{item} - Not found")
            all_good = False
    except Exception as e:
        print(f"✗ {module}.{item} - {type(e).__name__}: {e}")
        all_good = False

print("-" * 50)
if all_good:
    print("✓ All imports successful!")
    sys.exit(0)
else:
    print("✗ Some imports failed")
    sys.exit(1)
