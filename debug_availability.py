from app import create_app, db
from app.models import Neighborhood, User, EmployeeSchedule, Service
from datetime import date

app = create_app()

with app.app_context():
    print("--- Debugging Availability ---")
    
    # Check Services
    services = Service.query.all()
    print(f"Services count: {len(services)}")
    
    # Check Neighborhoods and Employees
    neighborhoods = Neighborhood.query.all()
    print(f"Neighborhoods count: {len(neighborhoods)}")
    
    for n in neighborhoods:
        employees = n.employees.filter_by(role='employee').all()
        print(f"Neighborhood: {n.name_ar} (ID: {n.id}) - Employees: {len(employees)}")
        
        for emp in employees:
            schedules = emp.schedules.filter_by(is_active=True).all()
            print(f"  Employee: {emp.username} (ID: {emp.id}) - Active Schedules: {len(schedules)}")
            for s in schedules:
                print(f"    Day: {s.day_of_week}, Time: {s.start_time} - {s.end_time}")

    print("--- End Debug ---")
