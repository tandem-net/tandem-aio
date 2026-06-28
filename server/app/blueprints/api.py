from flask import Blueprint, jsonify, request

from werkzeug.security import check_password_hash, generate_password_hash

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from extensions import db
from models import User, UserAPI

api_bp = Blueprint("api", __name__)

def _verify_credentials(username: str, password: str) -> bool:
    statement = select(User).where(
        User.username == username,
        User.password == password
    )
    user = db.session.scalars(statement).first()

    if not user:
        return False

    return check_password_hash(user.password, password)

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

@api_bp.route("/generate_api", methods=['POST'])
def generate_api():
    data = request.get_json(silent = True) or {}

    username = data.get("username")
    password = data.get("password")

    
    
    return jsonify({"status": "success"})