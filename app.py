from flask import Flask, jsonify
from config import Config
from extensions import db, bcrypt, jwt, mail
from routes.auth import auth_bp
from models import User

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    
    db.init_app(app)
    bcrypt.init_app(app)
    jwt.init_app(app)
    mail.init_app(app)
    
    app.register_blueprint(auth_bp)

    @app.get("/")
    def root():
        return jsonify({"status": "ok", "app": "Isuzulu Local Pass Backend"})

    return app

app = create_app()

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)
