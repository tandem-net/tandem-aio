from app.extensions import db, generate_api_key
from app.models import User, UserAPI
from flask import Blueprint, jsonify, request
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from werkzeug.security import check_password_hash, generate_password_hash

api_bp = Blueprint("api", __name__)


def _verify_credentials(username: str | None, password: str | None) -> User | None:
    if not username or not password:
        return None

    statement = select(User).where(User.username == username)

    user = db.session.scalars(statement).first()

    if user and user.password and check_password_hash(user.password, password):
        return user

    return None


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

    username = (data.get("username") or "").strip()
    password = data.get("password") or ""

    if not username or not password:
        return jsonify({"error": "Username and password are required"}), 400

    password_hash = generate_password_hash(password)

    try:
        new_user = User()
        new_user.username = username
        new_user.password = password_hash

        db.session.add(new_user)
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return jsonify({"error": "Username already exists"}), 400
    except Exception:
        db.session.rollback()
        return jsonify(
            {"error": "An unexpected error occurred, please try again."}
        ), 500

    return jsonify({"status": "success"}), 201


@api_bp.route("/generate_api", methods=["POST"])
def generate_api():
    data = request.get_json(silent=True) or {}

    username = data.get("username")
    password = data.get("password")

    user = _verify_credentials(username, password)

    if user is None:
        return jsonify({"status": "failure", "message": "Incorrect credentials"})

    api = generate_api_key()

    new_api_entry = UserAPI()
    new_api_entry.user_id = user.id
    new_api_entry.api_key = api

    try:
        db.session.add(new_api_entry)
        db.session.commit()
    except Exception:
        db.session.rollback()
        return jsonify(
            {
                "status": "failure",
                "message": "Internal database error, please try again",
            }
        ), 500
        # DOCUMENT: status is always either 'success' or 'failure'
        # the messae should always be 'message'

    return jsonify(
        {
            "status": "success",
            "message": "api key generated successfully",
            "api_key": api,
        }
    ), 201
