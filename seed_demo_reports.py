"""Insert demo bookings for the last 30 days so every report section can be checked by hand.

The scenario deliberately covers each case the reports have to handle:
single vehicle, multi-vehicle, large-vehicle surcharge, percentage and fixed
discounts, a free wash, a subscription wash, cancellations, a booking with no
area, work finished after midnight on a night shift, and open bookings.

Run it with:    python seed_demo_reports.py
Remove it with: python seed_demo_reports.py --remove

Every row it creates is recorded in demo_data_manifest.json, so --remove
deletes exactly what was added and nothing else.
"""

import json
import os
import sys
from datetime import date, datetime, time, timedelta

from app import create_app, db
from app.models import (Booking, BookingItem, BookingProduct, DiscountCode,
                        Product, Service, Subscription, SubscriptionPackage,
                        User, Vehicle)

MANIFEST = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        'demo_data_manifest.json')

# Existing reference rows in this database.
RIYADH, JEDDAH, MAKKAH = 1, 2, 3
HOOD_OLAYA, HOOD_MALQA = 6, 7          # الرياض
HOOD_RAWDA, HOOD_SHATI = 4, 5          # جدة
HOOD_NAWARIYA = 9                      # مكة المكرمة
SVC_OUT, SVC_FULL = 1, 2               # 35 ر.س / 60 ر.س
PRODUCT = 2                            # 50 ر.س
PACKAGE = 2                            # الباقة الذهبية 250 ر.س
EMP_A, EMP_B = 2, 8                    # employee / employee1
CUST_A, CUST_B, CUST_C, CUST_D = 3, 5, 6, 9
CAR_SMALL, CAR_MID = 1, 2              # both belong to CUST_A
CAR_B, CAR_C = 3, 4
LARGE_SIZE_SURCHARGE = 8.0


def record(manifest, table, obj):
    manifest.setdefault(table, []).append(obj.id)
    return obj


def add_booking(manifest, *, customer, employee, service, hood, day, at,
                status='completed', service_price=None, size_price=0.0,
                payment='cash', discount=None, free_wash=False,
                subscription=None, rating=None, products=(), items=(),
                cancel_reason=None, duration_minutes=None, vehicle=None):
    """Create one booking plus its items/products, mirroring the booking flow."""
    booking = Booking(
        customer_id=customer, employee_id=employee, service_id=service,
        vehicle_id=vehicle, neighborhood_id=hood, date=day, time=at,
        status=status, custom_service_price=service_price,
        vehicle_size_price=size_price, payment_method=payment,
        discount_code_id=discount, used_free_wash=free_wash,
        subscription_id=subscription, rating=rating,
        is_multi_vehicle=len(items) > 1,
        cancellation_reason=cancel_reason,
        created_at=datetime.combine(day, at),
    )
    if status == 'completed' and duration_minutes:
        booking.started_at = datetime.combine(day, at)
        booking.completed_at = booking.started_at + timedelta(minutes=duration_minutes)
    if status == 'cancelled':
        booking.cancelled_at = datetime.combine(day, at) + timedelta(minutes=20)
    db.session.add(booking)
    db.session.flush()
    record(manifest, 'booking', booking)

    services_total = 0.0
    for item_vehicle, item_service, item_price, item_size in items:
        total = 0.0 if free_wash and not services_total else item_price + item_size
        services_total += total
        row = BookingItem(booking_id=booking.id, vehicle_id=item_vehicle,
                          service_id=item_service, quantity=1,
                          service_price=item_price, size_price_adjustment=item_size,
                          total_item_price=total)
        db.session.add(row)
        db.session.flush()
        record(manifest, 'booking_item', row)

    products_total = 0.0
    for product_id, quantity, unit_price in products:
        products_total += unit_price * quantity
        row = BookingProduct(booking_id=booking.id, product_id=product_id,
                             quantity=quantity, unit_price=unit_price)
        db.session.add(row)
        db.session.flush()
        record(manifest, 'booking_product', row)

    if not items:
        if subscription or free_wash:
            services_total = 0.0
        else:
            services_total = (service_price or 0) + (size_price or 0)

    discount_value = 0.0
    if discount:
        code = db.session.get(DiscountCode, discount)
        if code.discount_type == 'percentage':
            discount_value = services_total * (code.value / 100)
        else:
            discount_value = code.value
    booking.total_price = max(0.0, services_total + products_total - discount_value)
    return booking


def seed():
    manifest = {}
    today = date.today()

    # --- Discount codes ---------------------------------------------------
    pct = DiscountCode(code='DEMO20', discount_type='percentage', value=20,
                       valid_from=datetime.combine(today - timedelta(days=40), time(0)),
                       valid_until=datetime.combine(today + timedelta(days=40), time(0)),
                       is_active=True, max_uses_per_customer=None, used_count=0)
    fixed = DiscountCode(code='DEMO15SAR', discount_type='fixed', value=15,
                         valid_from=datetime.combine(today - timedelta(days=40), time(0)),
                         valid_until=datetime.combine(today + timedelta(days=40), time(0)),
                         is_active=True, max_uses_per_customer=None, used_count=0)
    db.session.add_all([pct, fixed])
    db.session.flush()
    record(manifest, 'discount_code', pct)
    record(manifest, 'discount_code', fixed)

    # --- Subscriptions ----------------------------------------------------
    # One per city, plus one that expires within 7 days to raise the alert.
    subs = []
    for hood, start_offset, end_offset, status in [
        (HOOD_OLAYA, 25, 5, 'active'),       # الرياض - ينتهي خلال 7 أيام
        (HOOD_RAWDA, 20, 10, 'active'),      # جدة
        (HOOD_NAWARIYA, 12, 18, 'active'),   # مكة المكرمة
    ]:
        sub = Subscription(customer_id=CUST_A if hood == HOOD_OLAYA else CUST_B,
                           employee_id=EMP_A, neighborhood_id=hood,
                           package_id=PACKAGE, remaining_washes=3,
                           start_date=today - timedelta(days=start_offset),
                           end_date=today + timedelta(days=end_offset),
                           status=status,
                           created_at=datetime.combine(today - timedelta(days=start_offset), time(9)))
        db.session.add(sub)
        db.session.flush()
        record(manifest, 'subscription', sub)
        subs.append(sub)

    def day_ago(n):
        return today - timedelta(days=n)

    # --- 1. Plain single-vehicle booking, cash, with products -------------
    add_booking(manifest, customer=CUST_A, employee=EMP_A, service=SVC_FULL,
                hood=HOOD_OLAYA, day=day_ago(26), at=time(10), vehicle=CAR_SMALL,
                service_price=60, size_price=0, payment='cash', rating=5,
                duration_minutes=95,
                products=[(PRODUCT, 2, 50.0)],
                items=[(CAR_SMALL, SVC_FULL, 60.0, 0.0)])

    # --- 2. Multi-vehicle booking: two cars, two services, card ----------
    # This is the case the reports used to undercount.
    add_booking(manifest, customer=CUST_A, employee=EMP_A, service=SVC_FULL,
                hood=HOOD_OLAYA, day=day_ago(24), at=time(12), vehicle=CAR_SMALL,
                service_price=60, size_price=0, payment='card', rating=4,
                duration_minutes=150,
                items=[(CAR_SMALL, SVC_FULL, 60.0, 0.0),
                       (CAR_MID, SVC_OUT, 35.0, 0.0)])

    # --- 3. Large vehicle surcharge --------------------------------------
    add_booking(manifest, customer=CUST_B, employee=EMP_B, service=SVC_FULL,
                hood=HOOD_MALQA, day=day_ago(22), at=time(16), vehicle=CAR_B,
                service_price=60, size_price=LARGE_SIZE_SURCHARGE, payment='card',
                rating=5, duration_minutes=110,
                items=[(CAR_B, SVC_FULL, 60.0, LARGE_SIZE_SURCHARGE)])

    # --- 4. Percentage discount 20% --------------------------------------
    add_booking(manifest, customer=CUST_C, employee=EMP_B, service=SVC_FULL,
                hood=HOOD_RAWDA, day=day_ago(20), at=time(11), vehicle=CAR_C,
                service_price=60, size_price=0, payment='cash', discount=pct.id,
                rating=3, duration_minutes=100,
                items=[(CAR_C, SVC_FULL, 60.0, 0.0)])

    # --- 5. Fixed discount 15 SAR, with a product ------------------------
    add_booking(manifest, customer=CUST_C, employee=EMP_B, service=SVC_OUT,
                hood=HOOD_SHATI, day=day_ago(18), at=time(13), vehicle=CAR_C,
                service_price=35, size_price=0, payment='card', discount=fixed.id,
                rating=4, duration_minutes=90,
                products=[(PRODUCT, 1, 50.0)],
                items=[(CAR_C, SVC_OUT, 35.0, 0.0)])

    # --- 6. Free wash: service is free, the product is still charged -----
    add_booking(manifest, customer=CUST_A, employee=EMP_A, service=SVC_FULL,
                hood=HOOD_OLAYA, day=day_ago(16), at=time(9), vehicle=CAR_SMALL,
                service_price=60, size_price=0, payment='cash', free_wash=True,
                rating=5, duration_minutes=100,
                products=[(PRODUCT, 1, 50.0)],
                items=[(CAR_SMALL, SVC_FULL, 60.0, 0.0)])

    # --- 7. Subscription wash: no service revenue, product only ----------
    add_booking(manifest, customer=CUST_A, employee=EMP_A, service=SVC_FULL,
                hood=HOOD_OLAYA, day=day_ago(14), at=time(15), vehicle=CAR_MID,
                subscription=subs[0].id, size_price=0, payment='cash', rating=5,
                duration_minutes=105,
                products=[(PRODUCT, 1, 50.0)])

    # --- 8. Subscription wash with no add-on: zero revenue ---------------
    add_booking(manifest, customer=CUST_B, employee=EMP_A, service=SVC_OUT,
                hood=HOOD_RAWDA, day=day_ago(13), at=time(17), vehicle=CAR_B,
                subscription=subs[1].id, size_price=0, payment='cash',
                duration_minutes=80)

    # --- 9. Cancelled booking with a reason ------------------------------
    add_booking(manifest, customer=CUST_C, employee=EMP_B, service=SVC_FULL,
                hood=HOOD_RAWDA, day=day_ago(12), at=time(14), vehicle=CAR_C,
                status='cancelled', service_price=60, size_price=0,
                cancel_reason='العميل غير متواجد',
                items=[(CAR_C, SVC_FULL, 60.0, 0.0)])

    # --- 10. Cancelled booking carrying a discount code ------------------
    # Its saving must NOT appear in the discount report.
    add_booking(manifest, customer=CUST_D, employee=EMP_B, service=SVC_FULL,
                hood=HOOD_SHATI, day=day_ago(11), at=time(18), vehicle=CAR_C,
                status='cancelled', service_price=60, size_price=0,
                discount=pct.id, cancel_reason='تغير الموعد',
                items=[(CAR_C, SVC_FULL, 60.0, 0.0)])

    # --- 11. Booking with no area at all --------------------------------
    # Used to be dropped from every revenue figure.
    add_booking(manifest, customer=CUST_D, employee=EMP_A, service=SVC_OUT,
                hood=None, day=day_ago(10), at=time(10), vehicle=CAR_C,
                service_price=45, size_price=0, payment='cash', rating=4,
                duration_minutes=85,
                items=[(CAR_C, SVC_OUT, 45.0, 0.0)])

    # --- 12. Makkah booking, so a third city appears --------------------
    add_booking(manifest, customer=CUST_D, employee=EMP_B, service=SVC_FULL,
                hood=HOOD_NAWARIYA, day=day_ago(9), at=time(19), vehicle=CAR_C,
                service_price=60, size_price=LARGE_SIZE_SURCHARGE, payment='card',
                rating=2, duration_minutes=130,
                products=[(PRODUCT, 3, 50.0)],
                items=[(CAR_C, SVC_FULL, 60.0, LARGE_SIZE_SURCHARGE)])

    # --- 13. Work finished after midnight on a night shift --------------
    # employee 2 works 08:00 -> 02:00 on Friday (4) and Saturday (5), so a
    # 01:00 booking belongs to the previous day's shift.
    night = day_ago(7)
    while night.weekday() not in (4, 5):
        night -= timedelta(days=1)
    after_midnight = night + timedelta(days=1)
    add_booking(manifest, customer=CUST_A, employee=EMP_A, service=SVC_FULL,
                hood=HOOD_OLAYA, day=after_midnight, at=time(1, 0), vehicle=CAR_SMALL,
                service_price=60, size_price=0, payment='cash', rating=5,
                duration_minutes=95,
                items=[(CAR_SMALL, SVC_FULL, 60.0, 0.0)])

    # --- 14. Open bookings in various states ----------------------------
    for offset, at, status in [(3, time(11), 'pending'), (2, time(13), 'assigned'),
                               (1, time(15), 'in_progress')]:
        add_booking(manifest, customer=CUST_B, employee=EMP_B, service=SVC_OUT,
                    hood=HOOD_MALQA, day=day_ago(offset), at=at, vehicle=CAR_B,
                    status=status, service_price=35, size_price=0,
                    items=[(CAR_B, SVC_OUT, 35.0, 0.0)])

    # --- 15. Today, so the dashboard card has something to show ---------
    add_booking(manifest, customer=CUST_A, employee=EMP_A, service=SVC_FULL,
                hood=HOOD_OLAYA, day=today, at=time(10), vehicle=CAR_SMALL,
                service_price=60, size_price=0, payment='cash', rating=5,
                duration_minutes=100,
                products=[(PRODUCT, 1, 50.0)],
                items=[(CAR_SMALL, SVC_FULL, 60.0, 0.0)])
    add_booking(manifest, customer=CUST_B, employee=EMP_B, service=SVC_OUT,
                hood=HOOD_MALQA, day=today, at=time(12), vehicle=CAR_B,
                service_price=35, size_price=0, payment='card', rating=4,
                duration_minutes=85,
                items=[(CAR_B, SVC_OUT, 35.0, 0.0)])

    pct.used_count = 2
    fixed.used_count = 1
    db.session.commit()

    with open(MANIFEST, 'w', encoding='utf-8') as handle:
        json.dump(manifest, handle, indent=2)
    return manifest


def remove():
    if not os.path.exists(MANIFEST):
        print('لا يوجد ملف demo_data_manifest.json - لم يتم إضافة بيانات تجربة.')
        return
    with open(MANIFEST, encoding='utf-8') as handle:
        manifest = json.load(handle)

    models = {
        'booking_product': BookingProduct, 'booking_item': BookingItem,
        'booking': Booking, 'subscription': Subscription,
        'discount_code': DiscountCode,
    }
    # Children first so foreign keys stay satisfied.
    for table in ['booking_product', 'booking_item', 'booking', 'subscription',
                  'discount_code']:
        ids = manifest.get(table, [])
        deleted = 0
        for row_id in ids:
            row = db.session.get(models[table], row_id)
            if row is not None:
                db.session.delete(row)
                deleted += 1
        print('  %-18s حذف %d من %d' % (table, deleted, len(ids)))
    db.session.commit()
    os.remove(MANIFEST)
    print('\nتم حذف بيانات التجربة.')


if __name__ == '__main__':
    app = create_app()
    with app.app_context():
        if '--remove' in sys.argv:
            remove()
        else:
            if os.path.exists(MANIFEST):
                print('بيانات التجربة مضافة بالفعل. احذفها أولاً:'
                      '\n  python seed_demo_reports.py --remove')
                sys.exit(1)
            created = seed()
            total = sum(len(v) for v in created.values())
            print('تمت إضافة %d سجل:' % total)
            for table, ids in sorted(created.items()):
                print('  %-18s %d' % (table, len(ids)))
            print('\nللحذف:  python seed_demo_reports.py --remove')
