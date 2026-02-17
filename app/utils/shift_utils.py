from datetime import datetime, timedelta, date, time
from app.models import EmployeeSchedule

def get_employee_current_shift_date(employee_id, current_datetime=None):
    """
    Determines the "logical date" for an employee's current shift.
    
    If an employee is working a night shift that started yesterday and spans into today 
    (e.g., 8 PM yesterday to 2 AM today), this function will return yesterday's date 
    as long as the current time is within that shift's window (or slightly after).
    
    Args:
        employee_id (int): The ID of the employee.
        current_datetime (datetime, optional): The current datetime. Defaults to now.
        
    Returns:
        date: The logical date of the shift.
    """
    if current_datetime is None:
        from app.utils.timezone import get_saudi_time
        current_datetime = get_saudi_time()
        
    today = current_datetime.date()
    yesterday = today - timedelta(days=1)
    
    # Check if there was a night shift yesterday that extends to today
    # meaningful_night_shift: starts yesterday, ends today
    
    # complex logic: 
    # We need to check if 'yesterday' had a schedule where end_time <= start_time (night shift)
    # AND if current_time < end_time of that shift.
    
    yesterday_day_of_week = yesterday.weekday() # 0=Monday
    
    yesterday_schedules = EmployeeSchedule.query.filter_by(
        employee_id=employee_id,
        day_of_week=yesterday_day_of_week,
        is_active=True
    ).all()
    
    current_time = current_datetime.time()
    
    for schedule in yesterday_schedules:
        # Check for night shift
        if schedule.end_time <= schedule.start_time:
            # It's a night shift. ex: 20:00 -> 02:00
            # If current time is 01:00, it is < 02:00. So we are still in yesterday's shift.
            if current_time < schedule.end_time:
                return yesterday
                
    # If not in a previous day's extended shift, return today
    return today
