# Fix duplicate vehicleSelect declaration
with open('app/templates/customer/booking_form.html', 'r', encoding='utf-8') as f:
    content = f.read()

# Replace the second declaration with just a reference (no const)
old_duplicate = '''        // Fetch vehicle size price
        const vehicleSelect = document.querySelector('[name="vehicle_id"]');
        const vehicleId = vehicleSelect.value;'''

new_reference = '''        // Fetch vehicle size price
        const vehicleId = vehicleSelect.value;'''

content = content.replace(old_duplicate, new_reference)

with open('app/templates/customer/booking_form.html', 'w', encoding='utf-8') as f:
    f.write(content)

print("✅ Fixed duplicate vehicleSelect declaration")
