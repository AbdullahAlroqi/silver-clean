from flask import Blueprint

bp = Blueprint('employee', __name__)

from app.employee import routes
