"""Central permission policy for site-wide supervisors."""

SITE_PERMISSION_CHOICES = (
    ('dashboard', 'عرض لوحة التحكم'),
    ('bookings_view', 'عرض الحجوزات'), ('bookings_manage', 'إنشاء وتعديل الحجوزات وحالاتها'),
    ('subscriptions_view', 'عرض الاشتراكات والتلميع والهدايا'), ('subscriptions_manage', 'إدارة الاشتراكات والتلميع والهدايا'),
    ('employees_view', 'عرض الموظفين والجداول'), ('employees_manage', 'إضافة وتعديل الموظفين والجداول'),
    ('customers_view', 'عرض العملاء والتقييمات'), ('customers_manage', 'تعديل العملاء والنقاط والحظر'), ('customers_export', 'تصدير بيانات العملاء'),
    ('inventory_view', 'عرض المنتجات والمخزون'), ('inventory_manage', 'إدارة المنتجات والمخزون والمستودعات'),
    ('discounts_view', 'عرض الخصوم والسلات المتروكة'), ('discounts_manage', 'إنشاء وتعديل الخصوم'),
    ('reports_view', 'عرض التقارير التشغيلية والإدارية'), ('tracking_view', 'عرض تتبع الموظفين'),
    ('catalog_view', 'عرض الخدمات والباقات والمواسم'), ('catalog_manage', 'إدارة الخدمات والباقات والأسعار والمواسم'),
    ('locations_view', 'عرض المدن والأحياء'), ('locations_manage', 'إضافة وتعديل المدن والأحياء'),
    ('marketing_view', 'عرض الإحالات والمؤثرين والإعلانات'), ('marketing_manage', 'إدارة المؤثرين والإعلانات'),
    ('notifications_send', 'إرسال الإشعارات'),
    ('settings_view', 'عرض إعدادات الموقع والولاء'), ('settings_manage', 'تعديل إعدادات الموقع والولاء'), ('settings_backup', 'تنزيل النسخة الاحتياطية'),
    ('audit_view', 'عرض سجل التدقيق'), ('audit_export', 'تصدير سجل التدقيق'),
    ('delete_records', 'حذف السجلات (يتطلب أيضًا صلاحية إدارة القسم)'),
)

SITE_PERMISSION_KEYS = {key for key, _ in SITE_PERMISSION_CHOICES}

LEGACY_PERMISSION_MAP = {
    key: {f'{key}_view', f'{key}_manage'}
    for key in ('bookings', 'subscriptions', 'employees', 'customers', 'inventory',
                'discounts', 'catalog', 'locations', 'marketing', 'settings')
}
LEGACY_PERMISSION_MAP.update({
    'reports': {'reports_view'}, 'tracking': {'tracking_view'},
    'notifications': {'notifications_send'},
    'audit': {'audit_view', 'audit_export'},
})

ENDPOINT_PERMISSIONS = {
    'admin.index': 'dashboard',
    'admin.audit_logs': 'audit', 'admin.export_audit_logs': 'audit',
    'admin.employees': 'employees', 'admin.add_employee': 'employees',
    'admin.edit_employee': 'employees', 'admin.toggle_employee_break': 'employees',
    'admin.employee_schedule': 'employees', 'admin.employee_stats': 'employees',
    'admin.employees_by_neighborhood': 'employees',
    'admin.customers': 'customers', 'admin.reset_customer_password': 'customers',
    'admin.add_points': 'customers', 'admin.update_washes': 'customers',
    'admin.ban_customer': 'customers', 'admin.unban_customer': 'customers',
    'admin.banned_customers': 'customers', 'admin.customer_stats': 'customers',
    'admin.edit_customer': 'customers', 'admin.ratings': 'customers',
    'admin.export_customers': 'customers',
    'admin.products': 'inventory', 'admin.update_stock': 'inventory',
    'admin.get_location_stock': 'inventory', 'admin.add_warehouse': 'inventory',
    'admin.edit_warehouse': 'inventory', 'admin.product_stats': 'inventory',
    'admin.get_available_products_api': 'inventory',
    'admin.bookings': 'bookings', 'admin.create_booking': 'bookings',
    'admin.edit_booking': 'bookings', 'admin.update_booking_totals': 'bookings',
    'admin.refund_product': 'bookings', 'admin.add_booking_product': 'bookings',
    'admin.get_booking_items_api': 'bookings', 'admin.get_booking_products_api': 'bookings',
    'admin.get_customer_vehicles': 'bookings', 'admin.search_customers': 'bookings',
    'admin.get_available_slots': 'bookings', 'admin.get_area_available_slots': 'bookings',
    'admin.reassign_booking': 'bookings', 'admin.advance_booking_status': 'bookings',
    'admin.cancel_booking': 'bookings',
    'admin.subscriptions': 'subscriptions', 'admin.create_subscription': 'subscriptions',
    'admin.approve_subscription': 'subscriptions', 'admin.reject_subscription': 'subscriptions',
    'admin.reassign_subscription': 'subscriptions', 'admin.edit_subscription': 'subscriptions',
    'admin.whatsapp_customer': 'subscriptions', 'admin.polishing_orders': 'subscriptions',
    'admin.accept_polishing_order': 'subscriptions', 'admin.complete_polishing_order': 'subscriptions',
    'admin.reject_polishing_order': 'subscriptions', 'admin.gift_orders': 'subscriptions',
    'admin.accept_gift_order': 'subscriptions', 'admin.reject_gift_order': 'subscriptions',
    'admin.reports': 'reports', 'admin.management_reports': 'reports',
    'admin.employee_tracking': 'tracking', 'admin.get_employee_locations': 'tracking',
    'admin.discount_codes': 'discounts', 'admin.add_discount_code': 'discounts',
    'admin.edit_discount_code': 'discounts', 'admin.discount_code_stats': 'discounts',
    'admin.abandoned_checkouts': 'discounts',
    'admin.create_abandoned_checkout_discount': 'discounts',
    'admin.delete_abandoned_checkout_discount': 'discounts',
    'admin.services': 'catalog', 'admin.add_service': 'catalog',
    'admin.edit_service': 'catalog', 'admin.vehicle_sizes': 'catalog',
    'admin.add_vehicle_size': 'catalog', 'admin.edit_vehicle_size': 'catalog',
    'admin.packages': 'catalog', 'admin.add_package': 'catalog', 'admin.edit_package': 'catalog',
    'admin.assign_package_to_city': 'catalog', 'admin.update_package_city_price': 'catalog',
    'admin.remove_package_city_price': 'catalog', 'admin.get_city_package_prices': 'catalog',
    'admin.seasons': 'catalog', 'admin.add_season': 'catalog', 'admin.edit_season': 'catalog',
    'admin.assign_service_to_city_size': 'catalog', 'admin.update_service_city_price': 'catalog',
    'admin.remove_service_city_price': 'catalog', 'admin.get_city_service_prices': 'catalog',
    'admin.duplicate_service': 'catalog', 'admin.add_product': 'inventory',
    'admin.edit_product': 'inventory', 'admin.assign_product_to_city': 'inventory',
    'admin.update_product_city_price': 'inventory', 'admin.remove_product_city_price': 'inventory',
    'admin.get_city_product_prices': 'inventory', 'admin.duplicate_product': 'inventory',
    'admin.locations': 'locations', 'admin.add_city': 'locations',
    'admin.edit_city': 'locations', 'admin.add_neighborhood': 'locations',
    'admin.edit_neighborhood': 'locations', 'admin.get_neighborhood_boundary': 'locations',
    'admin.referral_tracking': 'marketing', 'admin.influencer_codes': 'marketing',
    'admin.add_influencer_code': 'marketing', 'admin.edit_influencer_code': 'marketing',
    'admin.toggle_influencer_code': 'marketing', 'admin.announcements': 'marketing',
    'admin.add_announcement': 'marketing', 'admin.edit_announcement': 'marketing',
    'admin.toggle_announcement': 'marketing', 'admin.send_notification': 'notifications',
    'admin.loyalty_settings': 'settings', 'admin.backup_json': 'settings',
    'admin.settings': 'settings',
}

DELETE_ENDPOINTS = {
    'admin.delete_employee', 'admin.delete_customer', 'admin.delete_subscription',
    'admin.delete_polishing_order', 'admin.delete_booking_item', 'admin.delete_booking',
    'admin.delete_service', 'admin.delete_vehicle_size', 'admin.delete_product',
    'admin.delete_warehouse', 'admin.delete_city', 'admin.delete_neighborhood',
    'admin.delete_package', 'admin.delete_season', 'admin.delete_discount_code',
    'admin.delete_announcement', 'admin.delete_influencer_code',
}

DELETE_ENDPOINT_PERMISSIONS = {
    'admin.delete_employee': 'employees', 'admin.delete_customer': 'customers',
    'admin.delete_subscription': 'subscriptions', 'admin.delete_polishing_order': 'subscriptions',
    'admin.delete_booking_item': 'bookings', 'admin.delete_booking': 'bookings',
    'admin.delete_service': 'catalog', 'admin.delete_vehicle_size': 'catalog',
    'admin.delete_product': 'inventory', 'admin.delete_warehouse': 'inventory',
    'admin.delete_city': 'locations', 'admin.delete_neighborhood': 'locations',
    'admin.delete_package': 'catalog', 'admin.delete_season': 'catalog',
    'admin.delete_discount_code': 'discounts', 'admin.delete_announcement': 'marketing',
    'admin.delete_influencer_code': 'marketing',
}

MANAGE_GET_ENDPOINTS = {
    'admin.add_employee', 'admin.edit_employee', 'admin.employee_schedule',
    'admin.edit_customer', 'admin.add_product', 'admin.edit_product',
    'admin.add_service', 'admin.edit_service', 'admin.add_vehicle_size',
    'admin.edit_vehicle_size', 'admin.add_package', 'admin.edit_package',
    'admin.add_season', 'admin.edit_season', 'admin.add_city', 'admin.edit_city',
    'admin.add_neighborhood', 'admin.edit_neighborhood',
    'admin.add_discount_code', 'admin.edit_discount_code',
    'admin.add_announcement', 'admin.edit_announcement',
    'admin.edit_influencer_code',
}

SPECIAL_ENDPOINT_PERMISSIONS = {
    'admin.export_customers': 'customers_export',
    'admin.export_audit_logs': 'audit_export',
    'admin.backup_json': 'settings_backup',
    'admin.send_notification': 'notifications_send',
}


def required_permission(endpoint, method='GET'):
    if endpoint in DELETE_ENDPOINTS:
        return 'delete_records'
    if endpoint in SPECIAL_ENDPOINT_PERMISSIONS:
        return SPECIAL_ENDPOINT_PERMISSIONS[endpoint]
    base = ENDPOINT_PERMISSIONS.get(endpoint)
    if not base or base in {'dashboard'}:
        return base
    if base in {'reports', 'tracking'}:
        return f'{base}_view'
    action = 'manage' if method not in {'GET', 'HEAD', 'OPTIONS'} or endpoint in MANAGE_GET_ENDPOINTS else 'view'
    return f'{base}_{action}'
