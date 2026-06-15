from flask import Blueprint, request, jsonify
import time
import requests
import json

from app.extensions import redis_client

nodes_bp = Blueprint('nodes', __name__)

def upload_test():
    pass

def download_test():
    pass

def latency():
    pass

@app.route('/upload', methods=['POST'])
def upload():
    pass

@app.route('/download', methods=['POST'])
def download():
    pass

@app.route('/ping', methods=['POST'])
def ping():
    pass

@app.route('/register', methods=['POST'])
def register():
    pass
