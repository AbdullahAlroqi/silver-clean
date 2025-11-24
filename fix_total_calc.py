# Fix booking form to calculate total AFTER fetching vehicle size price
with open('app/templates/customer/booking_form.html', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Find the updateOrderReview function and rewrite the pricing logic
content = ''.join(lines)

# Find the section that needs fixing
old_section = '''        // Fetch vehicle size price
        const vehicleId = vehicleSelect.value;
        if (vehicleId) {
            fetch(`/customer/api/vehicle/${vehicleId}/size-price`)
                .then(response => response.json())
                .then(data => {
                    vehicleSizePrice = data.size_price || 0;
                    const totalServicePrice = servicePrice + vehicleSizePrice;
                    document.getElementById('review-service-price').textContent = totalServicePrice + ' ریال';
                    // Continue with products calculation
                })
                .catch(error => {
                    console.error('Error fetching vehicle size price:', error);
                    vehicleSizePrice = 0;
                });
        } else {
            vehicleSizePrice = 0;
            document.getElementById('review-service-price').textContent = servicePrice + ' ریال';
        }

        // Products'''

new_section = '''        // Fetch vehicle size price
        const vehicleId = vehicleSelect.value;
        
        // Function to calculate totals (will be called after getting vehicle size price)
        const calculateTotals = () => {
            const totalServicePrice = servicePrice + vehicleSizePrice;
            document.getElementById('review-service-price').textContent = totalServicePrice + ' ریال';
            
            // Calculate product totals and grand total
            calculateProductsAndTotal();
        };
        
        if (vehicleId) {
            fetch(`/customer/api/vehicle/${vehicleId}/size-price`)
                .then(response => response.json())
                .then(data => {
                    vehicleSizePrice = data.size_price || 0;
                    calculateTotals();
                })
                .catch(error => {
                    console.error('Error fetching vehicle size price:', error);
                    vehicleSizePrice = 0;
                    calculateTotals();
                });
        } else {
            vehicleSizePrice = 0;
            calculateTotals();
        }
    }
    
    function calculateProductsAndTotal() {
        // Products'''

content = content.replace(old_section, new_section)

# Now wrap the products calculation in the new function
# Find where products calculation starts and ends
old_products = '''        // Products
        const selectedProducts = [];
        let productsTotal = 0;
        productsData.forEach(product => {
            const checkbox = document.querySelector(`input[name="product_${product.id}"]:checked`);
            if (checkbox) {
                const qty = parseInt(document.querySelector(`input[name="quantity_${product.id}"]`).value) || 1;
                const productTotal = product.price * qty;
                productsTotal += productTotal;
                selectedProducts.push({ name: product.name_ar, qty, price: product.price, total: productTotal });
            }
        });

        if (selectedProducts.length > 0) {
            let html = '';
            selectedProducts.forEach(p => {
                html += `<p><span class="text-gray-400">${p.name}: ${p.qty}x ${p.price} ریال</span> <span class="font-bold">${p.total} ریال</span></p>`;
            });
            document.getElementById('review-products-list').innerHTML = html;
            document.getElementById('review-products-section').style.display = 'block';
            document.getElementById('review-products-total').textContent = productsTotal + ' ریال';
            document.getElementById('review-products-total-row').style.display = 'flex';
        } else {
            document.getElementById('review-products-section').style.display = 'none';
            document.getElementById('review-products-total-row').style.display = 'none';
        }

        // Calculate total with discounts
        let total = (servicePrice + vehicleSizePrice) + productsTotal;'''

new_products = '''        const selectedProducts = [];
        let productsTotal = 0;
        productsData.forEach(product => {
            const checkbox = document.querySelector(`input[name="product_${product.id}"]:checked`);
            if (checkbox) {
                const qty = parseInt(document.querySelector(`input[name="quantity_${product.id}"]`).value) || 1;
                const productTotal = product.price * qty;
                productsTotal += productTotal;
                selectedProducts.push({ name: product.name_ar, qty, price: product.price, total: productTotal });
            }
        });

        if (selectedProducts.length > 0) {
            let html = '';
            selectedProducts.forEach(p => {
                html += `<p><span class="text-gray-400">${p.name}: ${p.qty}x ${p.price} ریال</span> <span class="font-bold">${p.total} ریال</span></p>`;
            });
            document.getElementById('review-products-list').innerHTML = html;
            document.getElementById('review-products-section').style.display = 'block';
            document.getElementById('review-products-total').textContent = productsTotal + ' ریال';
            document.getElementById('review-products-total-row').style.display = 'flex';
        } else {
            document.getElementById('review-products-section').style.display = 'none';
            document.getElementById('review-products-total-row').style.display = 'none';
        }

        // Calculate total with discounts
        let total = (servicePrice + vehicleSizePrice) + productsTotal;'''

content = content.replace(old_products, new_products)

with open('app/templates/customer/booking_form.html', 'w', encoding='utf-8') as f:
    f.write(content)

print("✅ Fixed booking form to calculate total after fetching vehicle size price")
