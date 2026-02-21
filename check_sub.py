import sqlite3

conn = sqlite3.connect(r'instance\silver_clean.db')
c = conn.cursor()

# Check subscription 62
c.execute('SELECT id, neighborhood_id, status, remaining_washes FROM subscription WHERE id=62')
row = c.fetchone()
print(f'Subscription 62: {row}')

if row:
    neigh_id = row[1]
    
    # Check services
    c.execute('SELECT id, name_ar, duration FROM service LIMIT 5')
    print(f'Services: {c.fetchall()}')
    
    # Check employees in this neighborhood
    c.execute("""
        SELECT u.id, u.username 
        FROM user u 
        JOIN employee_neighborhoods en ON u.id = en.employee_id 
        WHERE en.neighborhood_id = ? AND u.role = 'employee'
    """, (neigh_id,))
    emps = c.fetchall()
    print(f'Employees in neighborhood {neigh_id}: {emps}')
    
    # Check schedules for each employee
    from datetime import datetime
    today_dow = datetime.now().weekday()
    print(f'Today is day_of_week={today_dow}')
    
    for e in emps:
        c.execute("""
            SELECT day_of_week, start_time, end_time, is_active 
            FROM employee_schedule 
            WHERE employee_id = ? AND is_active = 1
        """, (e[0],))
        scheds = c.fetchall()
        print(f'  Employee {e[0]} ({e[1]}): {len(scheds)} active schedules')
        for s in scheds:
            print(f'    day={s[0]}, {s[1]}-{s[2]}')

conn.close()
