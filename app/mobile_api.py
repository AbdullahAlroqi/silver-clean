"""Endpoints used by the Android app's background service.

The app is a WebView, so it already holds the normal Flask session cookie; the
native service reuses that cookie, which is why these routes authenticate the
same way the website does. They are exempt from CSRF because a native client
has no page to read a token from -- the session cookie plus SameSite=Lax is the
protection here, and every route below is scoped to the logged-in user.
"""

from datetime import datetime

from flask import Blueprint, jsonify, request
from flask_login import current_user

from app import csrf, db
from app.models import EmployeeLocation, Notification

bp = Blueprint('mobile_api', __name__, url_prefix='/api/mobile')

# How many notifications a single poll may return, so a long-idle device
# cannot pull thousands of rows at once.
MAX_NOTIFICATIONS = 20


@bp.route('/session')
def session_info():
    """Tell the app who is logged in, so it only tracks employees."""
    if not current_user.is_authenticated:
        return jsonify({'authenticated': False})
    return jsonify({
        'authenticated': True,
        'user_id': current_user.id,
        'username': current_user.username,
        'role': current_user.role,
    })


@bp.route('/location', methods=['POST'])
@csrf.exempt
def update_location():
    """Store a position reported by the native background service."""
    if not current_user.is_authenticated:
        return jsonify({'status': 'unauthenticated'}), 401
    if current_user.role != 'employee':
        return jsonify({'status': 'forbidden'}), 403

    payload = request.get_json(silent=True) or {}
    try:
        latitude = float(payload['latitude'])
        longitude = float(payload['longitude'])
    except (KeyError, TypeError, ValueError):
        return jsonify({'status': 'invalid_payload'}), 400
    if not (-90 <= latitude <= 90) or not (-180 <= longitude <= 180):
        return jsonify({'status': 'invalid_coordinates'}), 400

    try:
        accuracy = float(payload.get('accuracy'))
    except (TypeError, ValueError):
        accuracy = None

    location = EmployeeLocation.query.filter_by(employee_id=current_user.id).first()
    if location is None:
        location = EmployeeLocation(employee_id=current_user.id)
        db.session.add(location)
    location.latitude = latitude
    location.longitude = longitude
    location.accuracy = accuracy
    location.is_tracking = True
    # A heartbeat resends the same coordinates, which would leave the row
    # unchanged and skip the onupdate hook, making the employee look stale.
    location.updated_at = datetime.utcnow()
    db.session.commit()
    return jsonify({'status': 'success'})


@bp.route('/notifications')
def notifications():
    """Return notifications newer than ``since_id`` for the logged-in user.

    The app remembers the highest id it has seen and passes it back, so nothing
    is shown twice and the website's own read/unread state is left untouched.
    """
    if not current_user.is_authenticated:
        return jsonify({'authenticated': False, 'notifications': []})

    since_id = request.args.get('since_id', type=int) or 0
    rows = (Notification.query
            .filter(Notification.user_id == current_user.id, Notification.id > since_id)
            .order_by(Notification.id.asc())
            .limit(MAX_NOTIFICATIONS)
            .all())

    return jsonify({
        'authenticated': True,
        'notifications': [{
            'id': row.id,
            'title': row.title or '',
            'message': row.message or '',
            'read': bool(row.read),
            'created_at': row.created_at.isoformat() if row.created_at else None,
        } for row in rows],
    })
