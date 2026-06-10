"""

"""

from flask import Blueprint, request, jsonify

from app.extensions import redis_client

deploy_bp = Blueprint('deploy', __name__)



@deploy_bp.route('/', methods=['POST'])
def deploy():
    pass