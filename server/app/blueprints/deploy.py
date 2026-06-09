from flask import Blueprint

deploy_bp = Blueprint('deploy', __name__)

@deploy_bp.route('/deploy', methods=['POST'])
def deploy():
    pass