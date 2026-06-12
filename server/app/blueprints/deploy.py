"""Deploy blueprint: generate a unique hex slug, cache in Redis,
and persist a record in the SQLite database via SQLAlchemy."""

from flask import Blueprint, request, jsonify
from app.extensions import db
from app.models import Deployment
import secrets

deploy_bp = Blueprint('deploy', __name__)


@deploy_bp.route('/', methods=['POST'])
def deploy():
    """
    Receives name, creates PID, and saves a
    deployment to db.
    """

    data = request.get_json() or {}
    name = data.get('name')

    if not name:
        return jsonify({'error': 'Name is required'})
    
    pid = secrets.token_hex(8)

    try:
        new_deployment = Deployment(name = name, pid = pid)
        db.session.add(new_deployment)
        db.session.commit()

        return jsonify({
            'message': 'Deployment Successful',
            'name': name,
            'pid': pid
        }), 201
    except Exception as e:
        db.session.rollback()

        return jsonify({
            'error': 'Oopsie with server',
            'details': str(e)
        }), 500

