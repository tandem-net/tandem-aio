from flask import Flask

from app.extensions import redis_client

def create_app():
    app = Flask(__name__)

    app.config['REDIS_URL'] = 'redis://localhost:6969/0'
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

    return app
