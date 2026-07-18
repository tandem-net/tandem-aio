import re

from app.extensions import db, generate_api_key
from app.models import User, UserAPI
from flask import Blueprint, jsonify, request
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from werkzeug.security import check_password_hash, generate_password_hash

api_bp = Blueprint("api", __name__)

_USERNAME_PATTERN = re.compile(r"^[A-Za-z0-9_.-]{3,64}$")
_MIN_PASSWORD_LENGTH = 8
_MAX_API_KEY_GENERATION_ATTEMPTS = 5


def _json_data() -> dict:
    data = request.get_json(silent=True) or {}
    return data if isinstance(data, dict) else {}


def _normalize_username(username: str | None) -> str:
    return (username or "").strip()


def _validate_registration_input(username: str, password: str) -> str | None:
    if not username or not password:
        return "Username and password are required"
    if not _USERNAME_PATTERN.fullmatch(username):
        return "Username must be 3-64 characters and contain only letters, numbers, dots, underscores, or hyphens"
    if len(password) < _MIN_PASSWORD_LENGTH:
        return f"Password must be at least {_MIN_PASSWORD_LENGTH} characters long"
    return None


def _verify_credentials(username: str | None, password: str | None) -> User | None:
    normalized_username = _normalize_username(username)
    if not normalized_username or not password:
        return None

    statement = select(User).where(User.username == normalized_username)
    user = db.session.scalars(statement).first()

    if user and user.password and check_password_hash(user.password, password):
        return user

    return None


def _issue_api_key(user: User, *, rotate_api_key: bool) -> tuple[str, bool]:
    existing_statement = (
        select(UserAPI).where(UserAPI.user_id == user.id).order_by(UserAPI.id.asc())
    )
    existing = db.session.scalars(existing_statement).first()

    if existing is not None and not rotate_api_key:
        return existing.api_key, False

    if rotate_api_key:
        for key in db.session.scalars(existing_statement).all():
            db.session.delete(key)
        db.session.flush()

    for _ in range(_MAX_API_KEY_GENERATION_ATTEMPTS):
        api_key = generate_api_key()
        already_exists = db.session.scalars(
            select(UserAPI).where(UserAPI.api_key == api_key)
        ).first()
        if already_exists is not None:
            continue

        new_api_entry = UserAPI()
        new_api_entry.user_id = user.id
        new_api_entry.api_key = api_key
        db.session.add(new_api_entry)
        return api_key, True

    raise RuntimeError("Could not generate a unique API key")


def _authenticate_and_issue_api_key(*, rotate_api_key: bool):
    data = _json_data()
    username = _normalize_username(data.get("username"))
    password = data.get("password") or ""

    user = _verify_credentials(username, password)
    if user is None:
        return jsonify({"status": "failure", "message": "Incorrect credentials"}), 401

    try:
        api_key, created_api_key = _issue_api_key(user, rotate_api_key=rotate_api_key)
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return (
            jsonify(
                {
                    "status": "failure",
                    "message": "Could not issue API key, please try again",
                }
            ),
            500,
        )
    except Exception:
        db.session.rollback()
        return (
            jsonify(
                {
                    "status": "failure",
                    "message": "Internal database error, please try again",
                }
            ),
            500,
        )

    return (
        jsonify(
            {
                "status": "success",
                "message": "authenticated successfully",
                "username": user.username,
                "api_key": api_key,
                "created_api_key": created_api_key,
            }
        ),
        200,
    )


@api_bp.route("/register", methods=["POST"])
def register():
    data = _json_data()

    username = _normalize_username(data.get("username"))
    password = data.get("password") or ""

    validation_error = _validate_registration_input(username, password)
    if validation_error is not None:
        return jsonify({"error": validation_error}), 400

    existing_user = db.session.scalars(
        select(User).where(User.username == username)
    ).first()
    if existing_user is not None:
        return jsonify({"error": "Username already exists"}), 409

    password_hash = generate_password_hash(password, method="scrypt")

    try:
        new_user = User()
        new_user.username = username
        new_user.password = password_hash

        db.session.add(new_user)
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return jsonify({"error": "Username already exists"}), 409
    except Exception:
        db.session.rollback()
        return jsonify(
            {"error": "An unexpected error occurred, please try again."}
        ), 500

    return jsonify({"status": "success"}), 201


@api_bp.route("/login", methods=["POST"])
def login():
    data = _json_data()
    rotate_api_key = bool(data.get("rotate_api_key"))
    return _authenticate_and_issue_api_key(rotate_api_key=rotate_api_key)


@api_bp.route("/generate_api", methods=["POST"])
def generate_api():
    data = _json_data()
    rotate_api_key = bool(data.get("rotate_api_key"))
    return _authenticate_and_issue_api_key(rotate_api_key=rotate_api_key)
