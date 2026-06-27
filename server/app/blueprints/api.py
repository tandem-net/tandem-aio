from flask import Blueprint, jsonify, request

from werkzeug.security import generate_password_hash
from sqlalchemy.exc import IntegrityError

from extensions import db
from models import User

api_bp = Blueprint("api", __name__)

@api_bp.route("/register", methods=["POST"])
def register():
    """
    Recieves data json from the CLI and creates a user.
    """
    
    """
    Data should be as follows:
        username
        password (hashed)

    email and phone number are asked when we have 2fa infra
    """
    data = request.get_json(silent=True) or {}


    username = data.get("username")
    password = data.get("password")

    if not username or not password:
        return jsonify({"error": "Username and password are required"}), 400

    password_hash = generate_password_hash(password)

    try:
        new_user = User(username=username, password=password_hash)
        db.session.add(new_user)
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return jsonify({"error": "Username already exists"}), 400
    except Exception:
        db.session.rollback()
        return jsonify({"error": "An unexpected error occurred, please try again."}), 500
        
    
    return jsonify({"status": "success"}), 201