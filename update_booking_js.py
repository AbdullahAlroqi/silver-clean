# Update booking_form.html JavaScript to include vehicle size price
with open('app/templates/customer/booking_form.html', 'r', encoding='utf-8') as f:
    content = f.read()

# Replace servicePrice variable declaration to include vehicle size
old_js_var = '''    let currentStep = 1;
    let servicePrice = 0;
    let productsData = [];'''

new_js_var = '''    let currentStep = 1;
    let servicePrice = 0;
    let vehicleSizePrice = 0;
    let productsData = [];'''

content = content.replace(old_js_var, new_js_var)

# Update the service price extraction to fetch vehicle size price too
old_price_extraction = '''        // Extract service price from service text (assumes format: "Service Name (XXX ريال)")
        const priceMatch = serviceTxt.match(/\\((\\d+(?:\\.\\d+)?)\\s*ريال\\)/);
        servicePrice = priceMatch ? parseFloat(priceMatch[1]) : 0;
        document.getElementById('review-service-price').textContent = servicePrice + ' ريال';'''

new_price_extraction = '''        // Extract service price from service text (assumes format: "Service Name (XXX ريال)")
        const priceMatch = serviceTxt.match(/\\((\\d+(?:\\.\\d+)?)\\s*ريال\\)/);
        servicePrice = priceMatch ? parseFloat(priceMatch[1]) : 0;
        
        // Fetch vehicle size price
        const vehicleSelect = document.querySelector('[name="vehicle_id"]');
        const vehicleId = vehicleSelect.value;
        if (vehicleId) {
            fetch(`/customer/api/vehicle/${vehicleId}/size-price`)
                .then(response => response.json())
                .then(data => {
                    vehicleSizePrice = data.size_price || 0;
                    const totalServicePrice = servicePrice + vehicleSizePrice;
                    document.getElementById('review-service-price').textContent = totalServicePrice + ' ريال';
                    updatePricing();
                });
        } else {
            vehicleSizePrice = 0;
            document.getElementById('review-service-price').textContent = servicePrice + ' ريال';
        }'''

content = content.replace(old_price_extraction, new_price_extraction)

# Update total calculation to use total service price
old_total_calc = '''            total = Math.max(0, servicePrice - discount) + productsTotal;'''
new_total_calc = '''            total = Math.max(0, (servicePrice + vehicleSizePrice) - discount) + productsTotal;'''

content = content.replace(old_total_calc, new_total_calc)

# Another location
old_total2 = '''        total = servicePrice + productsTotal;'''
new_total2 = '''        total = (servicePrice + vehicleSizePrice) + productsTotal;'''

content = content.replace(old_total2, new_total2)

writeit = open('app/templates/customer/booking_form.html', 'w', encoding='utf-8')
with open('app/templates/customer/booking_form.html', 'w', encoding='utf-8') as f:
    f.write(content)

print("✅ Updated booking_form.html to include vehicle size price in calculations")
