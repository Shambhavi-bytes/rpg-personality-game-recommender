from flask import Flask
from config import Config
from app.routes.narrative import narrative_bp   


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    app.register_blueprint(narrative_bp)   
    return app