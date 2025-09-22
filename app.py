# app.py
from datetime import timedelta
from flask import Flask, jsonify
from flask_cors import CORS

from config import Config
from extensions import db, bcrypt, jwt, mail
from routes import auth_bp  # imports from routes/__init__.py
from models import User

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # sensible defaults if missing
    app.config.setdefault("JWT_ACCESS_TOKEN_EXPIRES", timedelta(minutes=15))
    app.config.setdefault("JWT_REFRESH_TOKEN_EXPIRES", timedelta(days=30))
    app.config.setdefault("FRONTEND_BASE_URL", "http://192.168.109.124:3000")

    # init extensions on the *instance*
    db.init_app(app)
    bcrypt.init_app(app)
    jwt.init_app(app)
    mail.init_app(app)

    # CORS only here, on the *instance*
    CORS(app, resources={
        r"/auth/*": {
            "origins": [
                "http://localhost:3000",
                "http://127.0.0.1:3000",
                "http://192.168.109.124:3000",  # your LAN IP for CRA
            ],
            # if you later use http-only cookies:
            # "supports_credentials": True,
        }
    })

    # blueprints
    app.register_blueprint(auth_bp)

    @app.get("/")
    def root():
        return jsonify({"status": "ok", "app": "Isuzulu Local Pass Backend"})

    return app

app = create_app()

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
        # print(app.url_map)  # uncomment for sanity check
    app.run(host="0.0.0.0", port=5000, debug=True)
