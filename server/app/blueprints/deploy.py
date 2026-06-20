"""

Create a unique PID / slug and save it to an sqlalchemy db.

"""

from flask import Blueprint, request, jsonify
from app.extensions import db
from app.models import Deployment
from app.utils.toml_reader import parse_toml_string, extract_name, get_relevant
import secrets

deploy_bp = Blueprint('deploy', __name__)


@deploy_bp.route('/', methods=['POST'])
def deploy():
    """
    Receives name, creates PID, and saves a
    deployment to db.
    """

    data = request.get_json(silent=True) or {}

    name = None

    # toml file sent; default
    if 'toml_file' in request.files:
        toml_file = request.files['toml_file']
        parsed = parse_toml_string(toml_file)
        name = extract_name(parsed)

    # Fallback to JSON
    if not name:
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

