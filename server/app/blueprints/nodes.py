from flask import Blueprint, request, jsonify, Response

import time
import os
import shutil
import uuid

from app.extensions import redis_client

nodes_bp = Blueprint('nodes', __name__)

# 10MB of data
STREAM_SIZE_BYTES = 300 * 1024 * 1024
DUMMY_DATA = os.urandom(STREAM_SIZE_BYTES)

@nodes_bp.route('/download', methods=['GET'])
def download():
    return Response (
        DUMMY_DATA,
        mimetype = 'application/octet-stream',
        headers = {'Content-Length': str(STREAM_SIZE_BYTES)}
    )

@nodes_bp.route('/upload', methods=['POST'])
def upload():
    start_time = time.time()

    shutil.copyfileobj(request.stream, open(os.devnull, 'wb'))

    duration = time.time() - start_time

    return jsonify({'duration': duration})


@nodes_bp.route('/ping', methods=['POST'])
def ping():
    """
    Receives the final calculated metrics from the node.
    """

    data = request.get_json() or {}
    node_id = data.get('node_id')

    if not node_id:
        return jsonify({'error': "sorry bruzz you aren't registered / don't have a node_id"}), 400
    
    if not redis_client.exists(f"nodes:{node_id}"):
        return jsonify({'error': "node_id not found. Please register"}), 404
    
    metrics = {
        'latency': data.get('latency'),
        'download': data.get('download'),
        'upload': data.get('upload'),
        'last_seen': time.time()
    }

    redis_client.hmset(f"node:{node_id}", metrics)
    redis_client.sadd('nodes', node_id)

    return jsonify({'status': "Metrics Recorded"})

@nodes_bp.route('/health', methods=['POST'])
def health():
    data = request.get_json() or {}
    node_id = data.get('node_id')

    if not node_id:
        return jsonify({'error': "Missing node_id, bruzz pls register"}), 400
    
    if not redis_client.exists(f"node:{node_id}"):
        return jsonify({'error': "node_id not found. Please register"}), 404
    
    redis_client.hset(f"node:{node_id}", 'latency', data.get('latency'))
    redis_client.hset(f"node:{node_id}", 'last_seen', time.time())
    redis_client.sadd('nodes', node_id)

    return jsonify({'status': "Alive"})

@nodes_bp.route('/register', methods=['POST'])
def register():
    data = request.get_json() or {}

    node_id = f"node_{uuid.uuid4().hex[:12]}"

    metrics = {
        'latency': data.get('latency'),
        'download': data.get('download'),
        'upload': data.get('upload'),
        'last_seen': time.time()
    }

    redis_client.hmset(f"node:{node_id}", metrics)
    redis_client.sadd('nodes', node_id, node_id)

    return jsonify({
        'status': 'Registered',
        'node_id': node_id
    }), 201