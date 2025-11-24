# Update booking_form.html JavaScript to include vehicle size price
with open('app/templates/customer/booking_form.html', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Add vehicleSizePrice variable
if 'let vehicleSizePrice = 0;' not in content:
    content = content.replace(
        'let servicePrice = 0;',
        'let servicePrice = 0;\n    let vehicleSizePrice = 0;'
    )

# 2. Update updateOrderReview to fetch price
# We'll look for the service price extraction and append our logic
old_logic = '''        // Extract service price from service text (assumes format: "Service Name (XXX ريال)")
        const priceMatch = serviceTxt.match(/\((\d+(?:\.\d+)?)\s*ريال\)/);
        servicePrice = priceMatch ? parseFloat(priceMatch[1]) : 0;
        document.getElementById('review-service-price').textContent = servicePrice + ' ريال';'''

new_logic = '''        // Extract service price from service text (assumes format: "Service Name (XXX ريال)")
        const priceMatch = serviceTxt.match(/\((\d+(?:\.\d+)?)\s*ريال\)/);
        servicePrice = priceMatch ? parseFloat(priceMatch[1]) : 0;
        
        // Fetch vehicle size price
        const vehicleId = vehicleSelect.value;
        
        // Function to calculate totals (will be called after getting vehicle size price)
        const calculateTotals = () => {
            const totalServicePrice = servicePrice + vehicleSizePrice;
            document.getElementById('review-service-price').textContent = totalServicePrice + ' ريال';
            
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

    function calculateProductsAndTotal() {'''

# We need to be careful with the replacement. 
# The original code continues with "// Products"
# So we need to restructure the function a bit.

# Let's try a different approach: Replace the entire updateOrderReview function body part
# But first, let's make sure we have the calculateProductsAndTotal function
# Since it doesn't exist in the original file, we need to create it.

# Actually, let's just rewrite the whole updateOrderReview function and split it.
# It's safer to read the file, identify the function, and replace it.

# Let's use a simpler replacement for the variable first
content = content.replace('let servicePrice = 0;', 'let servicePrice = 0;\n    let vehicleSizePrice = 0;')

# Now let's replace the logic inside updateOrderReview
# We'll find the part where it calculates total and move it to a new function or wrap it.

# To avoid complex regex, let's just inject the fetch logic and modify the total calculation.
# We'll use a flag or just call a recalculate function.

# Let's try to match the block from "Extract service price" down to "document.getElementById('review-total').textContent"

# This is risky with string replacement if we don't match exactly.
# Let's look at what we have in the file (from previous view_file)

# The file has:
#         // Extract service price ...
#         const priceMatch = ...
#         servicePrice = ...
#         document.getElementById('review-service-price').textContent = servicePrice + ' ريال';
#
#         // Products
#         ...
#         // Calculate total
#         let total = servicePrice + productsTotal;

# We will replace this entire block.

start_marker = "// Extract service price from service text"
end_marker = "document.getElementById('review-total').textContent = total.toFixed(2) + ' ريال';"

start_idx = content.find(start_marker)
end_idx = content.find(end_marker)

if start_idx != -1 and end_idx != -1:
    end_idx += len(end_marker)
    
    new_block = '''// Extract service price from service text (assumes format: "Service Name (XXX ريال)")
        const priceMatch = serviceTxt.match(/\((\d+(?:\.\d+)?)\s*ريال\)/);
        servicePrice = priceMatch ? parseFloat(priceMatch[1]) : 0;
        
        // Fetch vehicle size price
        const vehicleId = vehicleSelect.value;
        
        if (vehicleId) {
            fetch(`/customer/api/vehicle/${vehicleId}/size-price`)
                .then(response => response.json())
                .then(data => {
                    vehicleSizePrice = data.size_price || 0;
                    updateTotals();
                })
                .catch(error => {
                    console.error('Error fetching vehicle size price:', error);
                    vehicleSizePrice = 0;
                    updateTotals();
                });
        } else {
            vehicleSizePrice = 0;
            updateTotals();
        }
    }

    function updateTotals() {
        const totalServicePrice = servicePrice + vehicleSizePrice;
        document.getElementById('review-service-price').textContent = totalServicePrice + ' ريال';

        // Products
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
            document.getElementById('review-products-section').style.display = 'block';
            document.getElementById('review-products-total-row').style.display = 'flex';
            document.getElementById('review-products-list').innerHTML = selectedProducts.map(p =>
                `<p>${p.name} × ${p.qty} = ${p.total} ريال</p>`
            ).join('');
            document.getElementById('review-products-total').textContent = productsTotal + ' ريال';
        } else {
            document.getElementById('review-products-section').style.display = 'none';
            document.getElementById('review-products-total-row').style.display = 'none';
        }

        // Calculate total
        let total = (servicePrice + vehicleSizePrice) + productsTotal;

        // Check for free wash
        const freeWash = document.getElementById('use_free_wash')?.checked || false;
        if (freeWash) {
            document.getElementById('review-free-wash-row').style.display = 'flex';
            document.getElementById('review-discount-row').style.display = 'none';
            total = productsTotal; // Free wash = service is free
        } else {
            document.getElementById('review-free-wash-row').style.display = 'none';

            // Check for discount code
            const discountValue = parseFloat(document.getElementById('discount_value').value) || 0;
            const discountType = document.getElementById('discount_type').value;
            const discountVerified = document.getElementById('discount_verified').value === '1';

            if (discountVerified && discountValue > 0) {
                let discount = 0;
                if (discountType === 'percentage') {
                    discount = (servicePrice * discountValue) / 100;
                } else {
                    discount = discountValue;
                }
                total = Math.max(0, (servicePrice + vehicleSizePrice) - discount) + productsTotal;
                document.getElementById('review-discount-row').style.display = 'flex';
                document.getElementById('review-discount').textContent = `- ${discount.toFixed(2)} ريال`;
            } else {
                document.getElementById('review-discount-row').style.display = 'none';
            }
        }

        document.getElementById('review-total').textContent = total.toFixed(2) + ' ريال';'''
        
    content = content[:start_idx] + new_block + content[end_idx:]
    
    with open('app/templates/customer/booking_form.html', 'w', encoding='utf-8') as f:
        f.write(content)
    print("✅ Updated booking_form.html with correct fetch logic")
else:
    print("❌ Could not find the code block to replace")
