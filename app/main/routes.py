from flask import render_template, Blueprint, request, jsonify, send_from_directory
from flask_login import login_required, current_user
from app.models import Notification, PushSubscription
from app import db
from app.main import bp
import os

@bp.route('/')
def index():
    return render_template('index.html')

@bp.route('/sw.js')
def service_worker():
    """Serve service worker from root to fix scope issue"""
    return send_from_directory(os.path.join(os.path.dirname(__file__), '..', 'static'), 
                                'sw.js', 
                                mimetype='application/javascript')

@bp.route('/notifications')
@login_required
def notifications():
    notifications = current_user.notifications.order_by(Notification.created_at.desc()).all()
    # Mark as read
    for n in notifications:
        n.read = True
    db.session.commit()
    return render_template('notifications.html', notifications=notifications)

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
        # Check if subscription already exists
        existing = PushSubscription.query.filter_by(endpoint=subscription_info['endpoint']).first()
        if not existing:
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
