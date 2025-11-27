#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Quick script to remove line 42 from base.html (orphaned {% endif %})
"""

file_path = r"app\templates\base.html"

with open(file_path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Remove line 42 (index 41)
if len(lines) > 41 and '{% endif %}' in lines[41]:
    print(f"Removing line 42: {lines[41].strip()}")
    del lines[41]
    
    with open(file_path, 'w', encoding='utf-8') as f:
        f.writelines(lines)
    print("✓ Fixed!")
else:
    print("Line 42 does not contain {% endif %} or file is too short")
    print(f"Line 42 content: {lines[41] if len(lines) > 41 else 'N/A'}")
