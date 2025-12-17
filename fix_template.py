"""Fix the Jinja2 template syntax in book_subscription_wash.html"""
import os

template_path = r'c:\Users\abdullah\Desktop\last update\test\app\templates\customer\book_subscription_wash.html'

# Read the file
with open(template_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Fix the broken pattern
broken_pattern = '{{ subscription.neighborhood_id }\n    };'
fixed_pattern = '{{ subscription.neighborhood_id }};\n        var serviceId = 1;'

# Also try the alternate broken pattern
broken_pattern2 = '        var neighborhoodId = {{ subscription.neighborhood_id }\n    };\n    var serviceId = 1;'
fixed_pattern2 = '        var neighborhoodId = {{ subscription.neighborhood_id }};\n        var serviceId = 1;'

if broken_pattern2 in content:
    content = content.replace(broken_pattern2, fixed_pattern2)
    print("Fixed pattern 2")
elif broken_pattern in content:
    content = content.replace(broken_pattern, fixed_pattern)
    print("Fixed pattern 1")
else:
    print("Pattern not found - checking content...")
    # Find the line with the issue
    lines = content.split('\n')
    for i, line in enumerate(lines):
        if 'neighborhoodId' in line:
            print(f"Line {i+1}: {line}")

# Write the file back
with open(template_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("Done")
