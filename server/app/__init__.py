from flask import Flask

def create_app():
    app = Flask(__name__)

    from app.blueprints.index import index_bp
    from app.blueprints.start import start_bp
    from app.blueprints.stop import stop_bp
    from app.blueprints.new import new_bp
    from app.blueprints.deploy import deploy_bp

    app.register_blueprint(index_bp)
    app.register_blueprint(start_bp)
    app.register_blueprint(stop_bp)
    app.register_blueprint(new_bp)
    app.register_blueprint(deploy_bp)

    return app
