from app import create_app
from datetime import date, timedelta

app = create_app()

with app.test_client() as client:
    print("--- Testing API ---")
    
    # Get a valid neighborhood and service
    with app.app_context():
        from app.models import Neighborhood, Service
        n = Neighborhood.query.first()
        s = Service.query.first()
        if not n or not s:
            print("No neighborhood or service found!")
            exit()
        
        n_id = n.id
        s_id = s.id
        print(f"Using Neighborhood ID: {n_id}, Service ID: {s_id}")
    
    # Test for tomorrow
    tomorrow = date.today() + timedelta(days=1)
    date_str = tomorrow.strftime('%Y-%m-%d')
    
    print(f"Testing for date: {date_str}")
    
    response = client.get(f'/customer/api/available-times?date={date_str}&neighborhood_id={n_id}&service_id={s_id}')
    
    print(f"Status Code: {response.status_code}")
    print(f"Response Data: {response.get_json()}")
    
    # Test for today
    today_str = date.today().strftime('%Y-%m-%d')
    print(f"Testing for today: {today_str}")
    response = client.get(f'/customer/api/available-times?date={today_str}&neighborhood_id={n_id}&service_id={s_id}')
    print(f"Status Code: {response.status_code}")
    print(f"Response Data: {response.get_json()}")
