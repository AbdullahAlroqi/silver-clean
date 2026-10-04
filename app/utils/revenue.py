"""Canonical revenue breakdown for a booking, shared by every report section.

Mirrors ``admin.routes.update_booking_totals`` so the numbers shown in reports
always agree with the total stored on the booking itself. In particular the
service side is summed from :class:`BookingItem` rows, so multi-vehicle orders
count every vehicle instead of only the first one.
"""

from collections import namedtuple

# ``discount`` is the saving actually realised on the order, i.e. gross minus
# net, so it never claims more than the booking was worth.
BookingRevenue = namedtuple('BookingRevenue', 'service product discount total')

# SQLite caps the number of bound parameters per statement, so preloading is
# done in chunks rather than one giant IN (...) clause.
_CHUNK_SIZE = 500


def _product_unit_price(booking_product):
    if booking_product.unit_price is not None:
        return booking_product.unit_price
    product = booking_product.product
    if product and product.price is not None:
        return product.price
    return 0


def booking_revenue(booking, items=None, products=None):
    """Split a booking into service/product revenue after discounts.

    ``items`` and ``products`` accept pre-loaded rows (see
    :func:`preload_booking_lines`) so reports can avoid a query per booking;
    both fall back to the booking's own relationships.
    """
    items = list(booking.items) if items is None else items
    products = list(booking.products) if products is None else products

    if items:
        service_gross = sum((item.total_item_price or 0) for item in items)
    elif booking.subscription_id or booking.used_free_wash:
        service_gross = 0
    else:
        base = booking.custom_service_price
        if base is None:
            base = booking.service.price if booking.service else 0
        service_gross = (base or 0) + (booking.vehicle_size_price or 0)

    product_gross = sum(
        _product_unit_price(bp) * (bp.quantity or 0) for bp in products
    )

    discount = 0
    code = booking.discount_code
    if code:
        if code.discount_type == 'percentage':
            discount = service_gross * ((code.value or 0) / 100)
        else:
            discount = code.value or 0

    # The discount comes off the services first and only then eats into the
    # products, so the two revenue cards always add up to the booking total.
    service_net = max(0, service_gross - discount)
    product_net = max(0, product_gross - (discount - (service_gross - service_net)))
    total_net = service_net + product_net
    return BookingRevenue(service_net, product_net,
                          (service_gross + product_gross) - total_net, total_net)


def booking_service_names(booking, items=None):
    """Every service sold in a booking - one entry per vehicle on multi-vehicle orders."""
    items = list(booking.items) if items is None else items
    if items:
        return [item.service.name_ar for item in items if item.service]
    return [booking.service.name_ar] if booking.service else []


def service_sales_totals(bookings):
    """Per-service ``{service_id: {'count', 'revenue'}}`` over the given bookings.

    Each vehicle served counts once, and an order-level discount is spread
    across that order's items in proportion to their price, so the revenue
    summed over all services equals the total service revenue.
    """
    items_by_booking, products_by_booking = preload_booking_lines(bookings)
    totals = {}

    def row_for(service_id):
        return totals.setdefault(service_id, {'count': 0, 'revenue': 0})

    for booking in bookings:
        items = items_by_booking.get(booking.id, [])
        net_service = booking_revenue(
            booking, items=items, products=products_by_booking.get(booking.id, [])
        ).service
        if items:
            gross = sum((item.total_item_price or 0) for item in items)
            for item in items:
                if not item.service_id:
                    continue
                row = row_for(item.service_id)
                row['count'] += 1
                share = ((item.total_item_price or 0) / gross) if gross else (1 / len(items))
                row['revenue'] += net_service * share
        elif booking.service_id:
            row = row_for(booking.service_id)
            row['count'] += 1
            row['revenue'] += net_service
    return totals


def preload_booking_lines(bookings):
    """Load items and products for many bookings up front.

    Returns ``(items_by_booking, products_by_booking)`` dictionaries suitable
    for passing straight into :func:`booking_revenue`, which keeps report pages
    at a couple of queries instead of two per booking.
    """
    from app.models import BookingItem, BookingProduct

    booking_ids = sorted({booking.id for booking in bookings if booking.id})
    items = {}
    products = {}
    for start in range(0, len(booking_ids), _CHUNK_SIZE):
        chunk = booking_ids[start:start + _CHUNK_SIZE]
        for row in BookingItem.query.filter(BookingItem.booking_id.in_(chunk)).all():
            items.setdefault(row.booking_id, []).append(row)
        for row in BookingProduct.query.filter(BookingProduct.booking_id.in_(chunk)).all():
            products.setdefault(row.booking_id, []).append(row)
    return items, products
