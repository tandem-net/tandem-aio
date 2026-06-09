from flask import Blueprint

start_bp = Blueprint('start', __name__)

@start_bp.route('/start', methods=['POST'])
def start():
    pass