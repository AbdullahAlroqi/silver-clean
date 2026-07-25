from datetime import datetime, time, timedelta


def employee_break_overlaps(employee, start, end):
    """Return whether an employee break overlaps the half-open interval [start, end)."""
    if not employee or not employee.is_on_break:
        return False

    if employee.break_type == 'date':
        if not employee.break_date:
            return False
        break_start = datetime.combine(employee.break_date, time.min)
        break_end = break_start + timedelta(days=1)
        return start < break_end and end > break_start

    if employee.break_type == 'time':
        if not employee.break_start_time or not employee.break_end_time:
            return False

        # Include the previous day because an overnight break can continue past midnight.
        day = start.date() - timedelta(days=1)
        last_day = end.date()
        while day <= last_day:
            break_start = datetime.combine(day, employee.break_start_time)
            break_end = datetime.combine(day, employee.break_end_time)
            if employee.break_end_time <= employee.break_start_time:
                break_end += timedelta(days=1)
            if start < break_end and end > break_start:
                return True
            day += timedelta(days=1)
        return False

    # full_day (and legacy rows without a type) remain unavailable until re-enabled.
    return True


def employee_on_break_at(employee, target_date=None, target_time=None):
    """Compatibility helper for checks that only have a date and/or a time."""
    if target_date and target_time:
        start = datetime.combine(target_date, target_time)
        return employee_break_overlaps(employee, start, start + timedelta(microseconds=1))
    if target_date:
        if not employee or not employee.is_on_break:
            return False
        if employee.break_type == 'date':
            return employee.break_date == target_date
        # A time break must be evaluated for each generated slot, not for the whole date.
        return employee.break_type in (None, 'full_day')
    return bool(employee and employee.is_on_break and employee.break_type in (None, 'full_day'))
