import json
from datetime import date, datetime, time

from flask import has_request_context, request
from flask_login import current_user
from sqlalchemy import event, inspect
from sqlalchemy.orm import Session


SENSITIVE_MARKERS = ('password', 'secret', 'token', 'csrf', 'private_key', 'auth', 'reset_code', 'push_subscription')
NOISY_MODELS = {'AuditLog', 'EmployeeLocation', 'CheckoutSession', 'Notification', 'PushSubscription'}


def _safe_value(value):
    if isinstance(value, (datetime, date, time)):
        return value.isoformat()
    if isinstance(value, bytes):
        return '<binary>'
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    return str(value)


def _is_sensitive(name):
    lowered = (name or '').lower()
    return any(marker in lowered for marker in SENSITIVE_MARKERS)


def _request_context():
    if not has_request_context():
        return None
    if not request.path.startswith('/admin') or request.method not in {'POST', 'PUT', 'PATCH', 'DELETE'}:
        return None
    if not current_user.is_authenticated or current_user.role not in {'admin', 'supervisor', 'site_supervisor'}:
        return None
    return {
        'actor_id': current_user.id,
        'actor_name': current_user.username or current_user.email or f'user-{current_user.id}',
        'actor_role': current_user.role,
        'endpoint': request.endpoint,
        'method': request.method,
        'path': request.full_path.rstrip('?')[:500],
        'ip_address': (request.access_route[0] if request.access_route else request.remote_addr),
        'user_agent': request.user_agent.string[:500],
    }


def _column_snapshot(obj):
    result = {}
    mapper = inspect(obj).mapper
    for column in mapper.columns:
        name = column.key
        result[name] = '<redacted>' if _is_sensitive(name) else _safe_value(getattr(obj, name, None))
    return result


def _changed_columns(obj):
    result = {}
    state = inspect(obj)
    for attribute in state.mapper.column_attrs:
        name = attribute.key
        history = state.attrs[name].history
        if not history.has_changes():
            continue
        if _is_sensitive(name):
            result[name] = {'old': '<redacted>', 'new': '<redacted>'}
        else:
            old = _safe_value(history.deleted[0]) if history.deleted else None
            new = _safe_value(history.added[0]) if history.added else _safe_value(getattr(obj, name, None))
            result[name] = {'old': old, 'new': new}
    return result


@event.listens_for(Session, 'before_flush')
def collect_admin_audit(session, flush_context, instances):
    context = _request_context()
    if not context or session.info.get('_adding_audit_logs'):
        return

    pending = session.info.setdefault('_pending_audit_logs', [])
    seen = session.info.setdefault('_audit_seen_objects', set())
    for action, objects in (('create', session.new), ('update', session.dirty), ('delete', session.deleted)):
        for obj in list(objects):
            model_name = obj.__class__.__name__
            identity = (action, id(obj))
            if model_name in NOISY_MODELS or identity in seen:
                continue
            if action == 'update' and not session.is_modified(obj, include_collections=False):
                continue
            changes = _column_snapshot(obj) if action in {'create', 'delete'} else _changed_columns(obj)
            if not changes:
                continue
            seen.add(identity)
            pending.append({'object': obj, 'action': action, 'entity_type': model_name,
                            'changes': changes, 'context': context.copy()})


@event.listens_for(Session, 'after_flush_postexec')
def write_admin_audit(session, flush_context):
    pending = session.info.pop('_pending_audit_logs', [])
    session.info.pop('_audit_seen_objects', None)
    if not pending:
        return
    from app.models import AuditLog

    session.info['_adding_audit_logs'] = True
    try:
        for item in pending:
            obj = item.pop('object')
            entity_id = getattr(obj, 'id', None)
            context = item.pop('context')
            session.add(AuditLog(
                **context,
                action=item['action'],
                entity_type=item['entity_type'],
                entity_id=str(entity_id) if entity_id is not None else None,
                changes_json=json.dumps(item['changes'], ensure_ascii=False, sort_keys=True),
            ))
    finally:
        session.info.pop('_adding_audit_logs', None)
