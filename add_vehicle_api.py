# Add API endpoint to get vehicle size price
with open('app/customer/routes.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Add this route after the book() function
api_route = '''
@bp.route('/api/vehicle/<int:vehicle_id>/size-price')
def get_vehicle_size_price(vehicle_id):
    """Get the size price for a vehicle"""
    vehicle = Vehicle.query.get_or_404(vehicle_id)
    size_price = vehicle.size.price_adjustment if vehicle.size else 0
    return jsonify({'size_price': size_price})
'''

# Find a good place to insert - after the book route
# Look for the end of book() function
insert_position = content.find('@bp.route(\'/api/')
if insert_position == -1:
    # If no API routes, add before vehicles route
    insert_position = content.find('@bp.route(\'/vehicles\')')
    
if insert_position != -1:
    # Insert the new route  
    content = content[:insert_position] + api_route + '\n' + content[insert_position:]
else:
    # Just append at the end
    content += '\n' + api_route

with open('app/customer/routes.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("✅ Added API endpoint for vehicle size price")
