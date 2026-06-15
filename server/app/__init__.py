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
        default_db_path = pathlib.Path(__file__).resolve().parents[1] / 'dev.db'
        database_uri = f"sqlite:///{default_db_path}"

    lower = database_uri.lower()
    allowed_prefixes = (
        'postgresql://',
        'postgres://',
        'postgresql+',
        'sqlite:///',
        'sqlite:'
    )
    if not any(lower.startswith(p) for p in allowed_prefixes):
        raise RuntimeError('DATABASE_URL must be a Postgres or SQLite URI (start with "postgresql://" or "sqlite:///")')

    app.config['SQLALCHEMY_DATABASE_URI'] = database_uri
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    redis_url = os.environ.get('REDIS_URL')
    if redis_url:
        app.config['REDIS_URL'] = redis_url

    redis_client.init_app(app)

    from app.blueprints.index import index_bp
    from app.blueprints.start import start_bp
    from app.blueprints.stop import stop_bp
    from app.blueprints.new import new_bp
    from app.blueprints.deploy import deploy_bp
    from app.blueprints.nodes import nodes_bp

    app.register_blueprint(index_bp, url_prefix='/')
    app.register_blueprint(start_bp, url_prefix='/start')
    app.register_blueprint(stop_bp, url_prefix='/stop')
    app.register_blueprint(new_bp, url_prefix='/new')
    app.register_blueprint(deploy_bp, url_prefix='/deploy')
    app.register_blueprint(nodes_bp, url_prefix='')

    with app.app_context():
        import importlib
        importlib.import_module('app.models')
        
        db.init_app(app)
        try:
            db.create_all()
        except Exception as e:
            print('Warning: could not create database tables at startup:', e)
            # continue without stopping the app; DB may be unavailable locally

    return app
