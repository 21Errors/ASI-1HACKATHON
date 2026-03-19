#!/usr/bin/env python3
import os
import sys

files_to_delete = [
    'backend/finder_fixed.py',
    'CONFIG_TEMPLATE.py',
    'create_structure.bat',
    'MANUAL_SETUP.md',
    'SETUP.py',
    '.env_new'
]

for f in files_to_delete:
    if os.path.exists(f):
        try:
            os.remove(f)
            print(f"Deleted: {f}")
        except Exception as e:
            print(f"Failed to delete {f}: {e}")
    else:
        print(f"Not found: {f}")

# Now list the directory
print("\nDirectory contents:")
for item in sorted(os.listdir('.')):
    if not item.startswith('__'):
        print(f"  {item}")

print("\nBackend contents:")
if os.path.isdir('backend'):
    for item in sorted(os.listdir('backend')):
        if not item.startswith('__'):
            print(f"  backend/{item}")
