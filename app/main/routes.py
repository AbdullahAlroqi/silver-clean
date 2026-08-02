from flask import render_template, Blueprint, request, jsonify, send_from_directory, make_response, redirect, url_for, flash
from flask_login import login_required, current_user
from app.models import Notification, PushSubscription
from app import db
from app.main import bp
import os
from datetime import datetime, timedelta

@bp.route('/')
def index():
    if current_user.is_authenticated:
        from app.auth.routes import get_post_login_redirect
        return redirect(get_post_login_redirect(current_user))
    return render_template('index.html')

@bp.route('/sw.js')
def service_worker():
    """Serve service worker from root to fix scope issue"""
    response = make_response(send_from_directory(
        os.path.join(os.path.dirname(__file__), '..', 'static'),
        'sw.js',
        mimetype='application/javascript'
    ))
    response.headers['Service-Worker-Allowed'] = '/'
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    return response

@bp.route('/manifest.json')
def manifest():
    """Serve a stable, standards-compliant web app manifest."""
    from app.models import SiteSettings
    
    settings = SiteSettings.get_settings()
    from flask import current_app
    from app.utils.pwa_icons import refresh_pwa_icons
    refresh_pwa_icons(current_app, settings.logo_path, settings.primary_color or '#303030')
    icon_version = int(settings.updated_at.timestamp()) if settings.updated_at else 1
    
    manifest_data = {
        "id": "/",
        "name": settings.site_name or "Silver Clean Car Wash",
        "short_name": settings.site_name or "Silver Clean",
        "description": "Silver Clean - خدمة غسيل سيارات متنقلة",
        "start_url": "/",
        "scope": "/",
        "display": "standalone",
        "display_override": ["standalone"],
        "orientation": "portrait",
        "background_color": settings.primary_color or "#1F1F1F",
        "theme_color": settings.accent_color or "#10B981",
        "categories": ["lifestyle", "business"],
        "launch_handler": {"client_mode": "navigate-existing"},
        "icons": [
            {
                "src": f"/static/images/pwa-icon-192.png?v={icon_version}",
                "sizes": "192x192",
                "type": "image/png",
                "purpose": "any maskable"
            },
            {
                "src": f"/static/images/pwa-icon-512.png?v={icon_version}",
                "sizes": "512x512",
                "type": "image/png",
                "purpose": "any maskable"
            }
        ],
        "gcm_sender_id": "103953800507"
    }
    
    response = jsonify(manifest_data)
    response.headers['Content-Type'] = 'application/manifest+json'
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    return response

@bp.route('/.well-known/appspecific/com.chrome.devtools.json')
def chrome_devtools_config():
    return jsonify({})

@bp.route('/notifications')
@login_required
def notifications():
    notifications = current_user.notifications.order_by(Notification.created_at.desc()).all()
    old_notifications_count = current_user.notifications.filter(
        Notification.created_at < datetime.utcnow() - timedelta(days=30)
    ).count()
    # Mark as read
    for n in notifications:
        n.read = True
    db.session.commit()
    if current_user.role == 'customer':
        layout_template = 'customer/base.html'
    elif current_user.role in ('admin', 'supervisor'):
        layout_template = 'admin/base.html'
    else:
        layout_template = 'base.html'
    return render_template(
        'notifications.html',
        notifications=notifications,
        old_notifications_count=old_notifications_count,
        layout_template=layout_template
    )


@bp.route('/notifications/<int:notification_id>/delete', methods=['POST'])
@login_required
def delete_notification(notification_id):
    notification = Notification.query.filter_by(
        id=notification_id, user_id=current_user.id
    ).first_or_404()
    db.session.delete(notification)
    db.session.commit()
    flash('تم حذف الإشعار', 'success')
    return redirect(url_for('main.notifications'))


@bp.route('/notifications/delete-old', methods=['POST'])
@login_required
def delete_old_notifications():
    cutoff = datetime.utcnow() - timedelta(days=30)
    deleted_count = current_user.notifications.filter(
        Notification.created_at < cutoff
    ).delete(synchronize_session=False)
    db.session.commit()
    if deleted_count:
        flash(f'تم حذف {deleted_count} من الإشعارات القديمة', 'success')
    else:
        flash('لا توجد إشعارات أقدم من 30 يومًا', 'info')
    return redirect(url_for('main.notifications'))

@bp.route('/api/notifications/unread-count')
@login_required
def unread_notifications_count():
    count = current_user.notifications.filter_by(read=False).count()
    return jsonify({'count': count})

@bp.route('/terms')
def terms():
    return render_template('terms.html', title='Terms and Conditions')

@bp.route('/subscribe', methods=['POST'])
def subscribe():
    subscription_info = request.get_json()
    if current_user.is_authenticated:
        if (not subscription_info or not subscription_info.get('endpoint') or
                not subscription_info.get('keys', {}).get('p256dh') or
                not subscription_info.get('keys', {}).get('auth')):
            return jsonify({'status': 'invalid_subscription'}), 400
        # Check if subscription already exists
        existing = PushSubscription.query.filter_by(endpoint=subscription_info['endpoint']).first()
        if existing:
            # Browsers may rotate encryption keys without changing the endpoint.
            existing.user_id = current_user.id
            existing.p256dh = subscription_info['keys']['p256dh']
            existing.auth = subscription_info['keys']['auth']
            db.session.commit()
            return jsonify({'status': 'updated'}), 200
        else:
            # Create new subscription
            sub = PushSubscription(
                user_id=current_user.id,
                endpoint=subscription_info['endpoint'],
                p256dh=subscription_info['keys']['p256dh'],
                auth=subscription_info['keys']['auth']
            )
            db.session.add(sub)
            db.session.commit()
            return jsonify({'status': 'success'}), 201
    return jsonify({'status': 'ignored'}), 200
