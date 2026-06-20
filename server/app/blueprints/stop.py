from flask import Blueprint

stop_bp = Blueprint('stop', __name__)

@stop_bp.route('/stop', methods=['POST'])
def stop():
    pass