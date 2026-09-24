import os
from flask import Flask
from config import Config
from database.db import init_db
from routes.auth import auth_bp
from routes.dashboard import dashboard_bp
from routes.api import api_bp
from routes.map_routes import map_bp

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    init_db()
    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(api_bp)
    app.register_blueprint(map_bp)
    return app

app = create_app()

if __name__ == "__main__":
    print("AI Landslide Early Warning & Monitoring")
    print("Demo mode:", Config.DEMO_MODE)
    print(f"Running on http://{Config.HOST}:{Config.PORT}")
    debug = os.getenv("FLASK_DEBUG", "0") == "1"
    app.run(host=Config.HOST, port=Config.PORT, debug=debug)
