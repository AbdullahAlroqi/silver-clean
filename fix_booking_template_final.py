
import os

file_path = r'c:\Users\abdullah\Desktop\last update\test\app\templates\customer\booking_form.html'

with open(file_path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

new_lines = []
skip_next = False
for i, line in enumerate(lines):
    if skip_next:
        skip_next = False
        continue
        
    if "if ({{ 'true' if current_user.free_washes > 0 else 'false' }" in line and "}}" not in line:
        new_lines.append(line.replace("{{ 'true' if current_user.free_washes > 0 else 'false' }", "{{ 'true' if current_user.free_washes > 0 else 'false' }}) {"))
        # Check if next line is the stray "}) {"
        if i + 1 < len(lines) and "}) {" in lines[i+1] and len(lines[i+1].strip()) == 3:
            skip_next = True
    else:
        new_lines.append(line)

with open(file_path, 'w', encoding='utf-8') as f:
    f.writelines(new_lines)
print("File fixed definitively")
