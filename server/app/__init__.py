import os
import pathlib
import secrets

from dotenv import load_dotenv
from flask import Flask
from sqlalchemy import text

from app.extensions import db, redis_client

load_dotenv()


def _apply_runtime_schema_migrations() -> None:
    engine = db.engine
    if engine.dialect.name != "postgresql":
        return

    statements = [
        "ALTER TABLE users ALTER COLUMN username TYPE VARCHAR(64)",
        "ALTER TABLE users ALTER COLUMN password TYPE VARCHAR(255)",
        "ALTER TABLE user_api_rel ALTER COLUMN api_key TYPE VARCHAR(128)",
        "ALTER TABLE deployments ALTER COLUMN api_key TYPE VARCHAR(128)",
        "ALTER TABLE deployments ALTER COLUMN name TYPE VARCHAR(128)",
    ]

    with engine.begin() as connection:
        for statement in statements:
            connection.execute(text(statement))

        connection.execute(
            text(
                "CREATE UNIQUE INDEX IF NOT EXISTS ix_users_username_unique ON users (username)"
            )
        )


def _resolve_node_registration_token(server_dir: pathlib.Path) -> str:
    """The bearer token a node must send to POST /nodes/register.

    An explicit TANDEM_NODE_REGISTRATION_TOKEN always wins. Otherwise we reuse
    (or generate once) a random token on disk -- the same idea as the JWT
    keypair in blueprints/auth.py -- so the server is never silently open to
    registration and nobody has to invent and copy a secret by hand."""
    env_token = os.environ.get("TANDEM_NODE_REGISTRATION_TOKEN")
    if env_token:
        return env_token

    token_path = server_dir / "keys" / "node_registration_token.txt"
    if token_path.exists():
        return token_path.read_text(encoding="utf-8").strip()

    token = secrets.token_urlsafe(32)
    token_path.parent.mkdir(parents=True, exist_ok=True)
    token_path.write_text(token, encoding="utf-8")
    token_path.chmod(0o600)

    print("")
    print("=" * 72)
    print("No TANDEM_NODE_REGISTRATION_TOKEN set -- generated a random one instead.")
    print(f"Saved to {token_path} (reused on every restart from here on).")
    print("")
    print("On any machine you want to register as a node, run:")
    print(f"  tandem settings set-registration-token {token}")
    print("=" * 72)
    print("")

    return token


def create_app():
    app = Flask(__name__)
    server_dir = pathlib.Path(__file__).resolve().parents[1]

    database_uri = os.environ.get("DATABASE_URL")
    if not database_uri:
        default_db_path = server_dir / "dev.db"
        database_uri = f"sqlite:///{default_db_path}"

    lower = database_uri.lower()
    allowed_prefixes = (
        "postgresql://",
        "postgres://",
        "postgresql+",
        "sqlite:///",
        "sqlite:",
    )
    if not any(lower.startswith(p) for p in allowed_prefixes):
        raise RuntimeError(
            'DATABASE_URL must be a Postgres or SQLite URI (start with "postgresql://" or "sqlite:///")'
        )

    app.config["SQLALCHEMY_DATABASE_URI"] = database_uri
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    redis_url = os.environ.get("REDIS_URL")
    if redis_url:
        app.config["REDIS_URL"] = redis_url

    task_storage_root = os.environ.get("TASK_STORAGE_ROOT")
    if task_storage_root:
        app.config["TASK_STORAGE_ROOT"] = task_storage_root

    app.config["NODE_REGISTRATION_TOKEN"] = _resolve_node_registration_token(server_dir)

    redis_client.init_app(app)

    # JWT key paths — can be overridden via environment variables
    app.config["JWT_PRIVATE_KEY_PATH"] = os.environ.get(
        "JWT_PRIVATE_KEY_PATH", "keys/jwt_private.pem"
    )
    app.config["JWT_PUBLIC_KEY_PATH"] = os.environ.get(
        "JWT_PUBLIC_KEY_PATH", "keys/jwt_public.pem"
    )

    from app.blueprints.api import api_bp
    from app.blueprints.auth import auth_bp
    from app.blueprints.deploy import deploy_bp
    from app.blueprints.desktop import desktop_bp
    from app.blueprints.index import index_bp
    from app.blueprints.nodes import nodes_bp
    from app.blueprints.start import start_bp

    app.register_blueprint(index_bp, url_prefix="/")
    app.register_blueprint(start_bp, url_prefix="/start")
    app.register_blueprint(deploy_bp, url_prefix="/deploy")
    app.register_blueprint(nodes_bp, url_prefix="/nodes")
    app.register_blueprint(api_bp, url_prefix="/api/v1")
    # JWT-based auth for CLI and Desktop app
    app.register_blueprint(auth_bp, url_prefix="/api/v1/auth")
    # Desktop/CLI-specific routes (require JWT)
    app.register_blueprint(desktop_bp, url_prefix="/api/v1/desktop")

    with app.app_context():
        import importlib

        importlib.import_module("app.models")

        db.init_app(app)
        try:
            db.create_all()
            _apply_runtime_schema_migrations()
        except Exception as e:
            print("Warning: could not create database tables at startup:", e)
            # continue without stopping the app; DB may be unavailable locally

    return app
