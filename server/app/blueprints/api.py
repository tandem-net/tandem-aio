from flask import Blueprint, jsonify, request

api_bp = Blueprint("api", __name__)

@api_bp.route("/register", methods=["POST"])
def register():
    data = request.get_json(silent=True) or {}

    """
    Data should be as follows:
        username
        password (hashed)

    email and phone number are asked when we have 2fa infra
    """

    credentials = {
        'username': data.get("username"),
        'password': data.get("password")
    }

    
    
    return jsonify({"status": "register"})