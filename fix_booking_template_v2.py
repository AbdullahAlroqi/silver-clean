
import os

file_path = r'c:\Users\abdullah\Desktop\last update\test\app\templates\customer\booking_form.html'

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Define the clean function
clean_function = """    // Function to check free wash availability based on service
    function checkFreeWashEligibility() {
        const serviceId = serviceSelect.value;
        const freeWashContainer = document.getElementById('free-wash-container');

        if (!freeWashCheckbox || !freeWashContainer) return;

        if (serviceId && serviceEligibility[serviceId] === false) {
            // Service does NOT include free wash
            freeWashCheckbox.checked = false;
            freeWashCheckbox.disabled = true;
            // Trigger change event to re-enable discount code if it was disabled
            freeWashCheckbox.dispatchEvent(new Event('change'));

            // Visual feedback
            freeWashContainer.classList.add('opacity-50', 'pointer-events-none');
            const warningMsg = document.getElementById('free-wash-warning');
            if (warningMsg) warningMsg.style.display = 'block';
        } else {
            // Service allows free wash or no service selected yet (and user has free washes)
            // Only re-enable if user actually has free washes
            if ({{ 'true' if current_user.free_washes > 0 else 'false' }}) {
                freeWashCheckbox.disabled = false;
                freeWashContainer.classList.remove('opacity-50', 'pointer-events-none');
            }
            const warningMsg = document.getElementById('free-wash-warning');
            if (warningMsg) warningMsg.style.display = 'none';
        }
    }"""

# Find the start of the problematic area and the end
import re

# We want to replace from line 661-ish down to where the function ends.
# But let's be safer and replace the whole block from the first event listener to the end of the function.

pattern = r'if \(dateInput\) dateInput\.addEventListener\(\'change\', loadAvailableTimes\);.*?function checkFreeWashEligibility\(\) \{.*?\}\s*\}'
# The above regex is a bit risky due to nested braces.

# Let's try a different approach. We know the whole block we want to replace.
# I'll just read lines and find indices.

with open(file_path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

start_index = -1
end_index = -1

for i, line in enumerate(lines):
    if "if (dateInput) dateInput.addEventListener('change', loadAvailableTimes);" in line and start_index == -1:
        start_index = i
    if "if (discountCodeInput) {" in line:
        end_index = i
        break

if start_index != -1 and end_index != -1:
    new_lines = lines[:start_index]
    new_lines.append("    if (dateInput) dateInput.addEventListener('change', loadAvailableTimes);\n")
    new_lines.append("    if (neighborhoodSelect) neighborhoodSelect.addEventListener('change', loadAvailableTimes);\n")
    new_lines.append("    if (serviceSelect) {\n")
    new_lines.append("        serviceSelect.addEventListener('change', loadAvailableTimes);\n")
    new_lines.append("        serviceSelect.addEventListener('change', checkFreeWashEligibility);\n")
    new_lines.append("    }\n\n")
    new_lines.append(clean_function + "\n\n")
    new_lines.extend(lines[end_index:])
    
    with open(file_path, 'w', encoding='utf-8') as f:
        f.writelines(new_lines)
    print("File fixed and cleaned")
else:
    print(f"Failed to find markers: start={start_index}, end={end_index}")
