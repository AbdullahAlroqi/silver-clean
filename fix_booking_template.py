
import os

file_path = r'c:\Users\abdullah\Desktop\last update\test\app\templates\customer\booking_form.html'

with open(file_path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

new_lines = []
for line in lines:
    # Fix the broken line
    if "if ({{ 'true' if current_user.free_washes > 0 else 'false' }" in line and "}}" not in line:
        new_lines.append(line.replace("{{ 'true' if current_user.free_washes > 0 else 'false' }", "{{ 'true' if current_user.free_washes > 0 else 'false' }}) {"))
    elif "}) {" in line and "if (" not in line and len(line.strip()) == 3: # catching the stray line 683
        continue # skip it
    else:
        new_lines.append(line)

with open(file_path, 'w', encoding='utf-8') as f:
    f.writelines(new_lines)
print("File fixed")
