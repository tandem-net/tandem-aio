"""
Start the Tandem app, create the Process ID and Task IDs.
Receive TOML and CloudPickle files.

*TIDs are not used by Mock-1. Currently, entire process is sent.
"""

from flask import Blueprint, request, jsonify

from app.extensions import redis_client
from app.utils.toml_reader import parse_toml_string, get_relevant, extract_name
import json

start_bp = Blueprint('start', __name__)

@start_bp.route('/', methods=['POST'])
def start():

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
    parsed = parse_toml_string(toml_file)
    relevant = get_relevant(parsed)
    name = extract_name(parsed)
    pickle_files = request.files.getlist('pickle_files')

    if not pickle_files:
        return jsonify({'error': 'No cloudpickle files provided'}), 400
    
    for pickle_file in pickle_files:
        filename = pickle_file.filename
        data = pickle_file.read()

        # TODO: transfer pickle to nodes.

        print(f"Received CloudPickles: {filename}, Size: {len(data)} bytes")
    
    return jsonify({
        'message': 'Start Success',
        'name': name,
        'pickles_received': len(pickle_files)
    }), 200