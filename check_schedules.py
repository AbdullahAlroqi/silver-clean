from app import create_app, db
from app.models import EmployeeSchedule, User

app = create_app()

with app.app_context():
    # Get the employee
    emp = User.query.filter_by(role='employee').first()
    
    if emp:
        print(f"\n=== Employee: {emp.username} (ID: {emp.id}) ===")
        
        schedules = EmployeeSchedule.query.filter_by(employee_id=emp.id).all()
        
        if schedules:
            print(f"\nFound {len(schedules)} schedule(s):")
            
            days_map = {
                0: 'Monday (الاثنين)',
                1: 'Tuesday (الثلاثاء)', 
                2: 'Wednesday (الأربعاء)',
                3: 'Thursday (الخميس)',
                4: 'Friday (الجمعة)',
                5: 'Saturday (السبت)',
                6: 'Sunday (الأحد)'
            }
            
            for s in schedules:
                day_name = days_map.get(s.day_of_week, f'Unknown ({s.day_of_week})')
                active = '✅' if s.is_active else '❌'
                print(f"  {active} {day_name}: {s.start_time} - {s.end_time}")
        else:
            print("\n❌ No schedules found!")
    else:
        print("\n❌ No employee found!")
    
    # Check today
    from datetime import date
    today = date.today()
    today_weekday = today.weekday()
    
    print(f"\n=== Today ===")
    print(f"Date: {today}")
    print(f"Weekday: {today_weekday} ({days_map.get(today_weekday, 'Unknown')})")
