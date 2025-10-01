# app.py
from datetime import timedelta
from flask import Flask, jsonify
from flask_cors import CORS
from sqlalchemy import text 
from config import Config
from extensions import db, bcrypt, jwt, mail
from routes import auth_bp  # imports from routes/__init__.py
from routes.corpus import corpus_bp  # ✅ new import
from models import User, Translation  # ✅ include Translation
from flask_jwt_extended import JWTManager
from models import RevokedToken




def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # sensible defaults if missing
    app.config.setdefault("JWT_ACCESS_TOKEN_EXPIRES", timedelta(minutes=15))
    app.config.setdefault("JWT_REFRESH_TOKEN_EXPIRES", timedelta(days=30))
    app.config.setdefault("FRONTEND_BASE_URL", "http://10.11.43.135:3000")

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
                "http://10.11.43.135:3000",
            ],
        },
        r"/corpus/*": {
            "origins": [
                "http://localhost:3000",
                "http://127.0.0.1:3000",
                "http://10.11.43.135:3000",
            ],
        }
    })


    # blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(corpus_bp, url_prefix="/corpus")  # ✅ add corpus

    @app.get("/")
    def root():
        return jsonify({"status": "ok", "app": "Isizulu Local Pass Backend"})
    
    @app.get("/api/test-db")
    def test_db_connection():
        try:
            # Test raw SQL connection
            result = db.session.execute(text('SELECT NOW() as current_time'))
            db_time = result.fetchone()
            
            return jsonify({
                "status": "success", 
                "message": "Database connected successfully!",
                "database_time": db_time[0].isoformat() if db_time else None,
                "database_url_prefix": app.config['SQLALCHEMY_DATABASE_URI'][:30] + "..." if app.config['SQLALCHEMY_DATABASE_URI'] else "Not configured"
            })
        except Exception as e:
            return jsonify({
                "status": "error",
                "message": "Database connection failed",
                "error": str(e)
            }), 500

    return app

jwt = JWTManager()

@jwt.token_in_blocklist_loader
def check_if_token_revoked(jwt_header, jwt_payload: dict):
    jti = jwt_payload["jti"]
    return RevokedToken.is_jti_blacklisted(jti)

app = create_app()

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(host="0.0.0.0", port=5000, debug=True)
