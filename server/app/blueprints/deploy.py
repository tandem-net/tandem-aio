"""
Deploy must transfers the following to the server:
- TOML file in case it updated
- All the CloudPickles to run

Deploy must send the files via ...
"""

from flask import Blueprint, request, jsonify

from app.extensions import redis_client

deploy_bp = Blueprint('deploy', __name__)



@deploy_bp.route('/', methods=['POST'])
def deploy():

    """
    POST Request

    Receives the TOML config file and CloudPickle files from the user.
    Content-Type: multipart/form-data

    Upload the TOML file under the field 'toml_file'
    Upload pickles under the field 'pickle_files'

    """

    if 'toml_file' not in request.files:
        return jsonify({'error': 'Missing TOML config file'}), 400
    
    toml_file = request.files['toml_file']
    toml_content = toml_file.read().decode('utf-8')
    pickle_files = request.files.getlist('pickle_files')

    if not pickle_files:
        return jsonify({'error': 'No cloudpickle files provided'}), 400
    
    for pickle_file in pickle_files:
        filename = pickle_file.filename
        data = pickle_file.read()

        # TODO: transfer pickle to nodes.

        print(f"Received CloudPickles: {filename}, Size: {len(data)} bytes")
    
    return jsonify({
        'message': 'Deployment Success',
        'pickles_received': len(pickle_files)
    }), 200