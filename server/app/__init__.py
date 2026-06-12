from flask import Flask
import os
import pathlib

from dotenv import load_dotenv

from app.extensions import redis_client, db

load_dotenv()


def create_app():
    app = Flask(__name__)

    database_uri = os.environ.get('DATABASE_URL')
    if not database_uri:
        raise RuntimeError(
            'DATABASE_URL must be set and point to a Postgres database (e.g. postgresql://user:pass@host:5432/db)'
        )

    lower = database_uri.lower()
    if not (lower.startswith('postgresql://') or lower.startswith('postgres://') or lower.startswith('postgresql+')):
        raise RuntimeError('DATABASE_URL must be a Postgres URI (start with "postgresql://" or "postgres://")')

    app.config['SQLALCHEMY_DATABASE_URI'] = database_uri
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    redis_url = os.environ.get('REDIS_URL')
    if redis_url:
        app.config['REDIS_URL'] = redis_url

    db.init_app(app)
    redis_client.init_app(app)

    from app.blueprints.index import index_bp
    from app.blueprints.start import start_bp
    from app.blueprints.stop import stop_bp
    from app.blueprints.new import new_bp
    from app.blueprints.deploy import deploy_bp

    app.register_blueprint(index_bp, '/')
    app.register_blueprint(start_bp, '/start')
    app.register_blueprint(stop_bp, '/stop')
    app.register_blueprint(new_bp, '/new')
    app.register_blueprint(deploy_bp, '/deploy')

    with app.app_context():
        import app.models
        db.create_all()

    return app
