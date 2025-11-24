# Re-add API endpoint for vehicle size price
with open('app/customer/routes.py', 'r', encoding='utf-8') as f:
    content = f.read()

api_route = '''
@bp.route('/api/vehicle/<int:vehicle_id>/size-price')
def get_vehicle_size_price(vehicle_id):
    """Get the size price for a vehicle"""
    vehicle = Vehicle.query.get_or_404(vehicle_id)
    size_price = vehicle.size.price_adjustment if vehicle.size else 0
    return jsonify({'size_price': size_price})
'''

# Check if it's already there (just in case grep missed it, though unlikely)
if '/api/vehicle/' not in content:
    # Append to the end of the file or before the last line if it's a comment
    content += '\n' + api_route
    
    with open('app/customer/routes.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("✅ Added API endpoint for vehicle size price")
else:
    print("⚠️ API endpoint already exists (grep might have failed)")
