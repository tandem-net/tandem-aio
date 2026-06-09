from flask import Blueprint

new_bp = Blueprint('new', __name__)

@new_bp.route('/new', methods=['POST'])
def new():
    pass