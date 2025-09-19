from flask import Blueprint, request, jsonify
from sqlalchemy.exc import IntegrityError
from extensions import db
from flask_mail import Message
from flask import current_app
from extensions import db, mail
from models import User
from flask_jwt_extended import (
    create_access_token, create_refresh_token,
    jwt_required, get_jwt_identity
)

auth_bp = Blueprint("auth", __name__, url_prefix="/auth")

@auth_bp.post("/register")
def register():
    data = request.get_json(force=True, silent=True) or {}
    email = (data.get("email") or "").strip().lower()
    password = data.get("password")
    full_name = data.get("full_name")

    if not email or not password:
        return jsonify({"error": "email and password are required"}), 400

    try:
        user = User(email=email, full_name=full_name)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return jsonify({"error": "email already registered"}), 409

    return jsonify({"message": "registered", "user": user.to_dict()}), 201

@auth_bp.post("/login")
def login():
    data = request.get_json(force=True, silent=True) or {}
    email = (data.get("email") or "").strip().lower()
    password = data.get("password")

    if not email or not password:
        return jsonify({"error": "email and password are required"}), 400

    user = User.query.filter_by(email=email).first()
    if not user or not user.check_password(password):
        return jsonify({"error": "invalid credentials"}), 401

    access = create_access_token(identity=user.id)
    refresh = create_refresh_token(identity=user.id)
    return jsonify({
        "access_token": access,
        "refresh_token": refresh,
        "user": user.to_dict()
    }), 200

@auth_bp.post("/refresh")
@jwt_required(refresh=True)
def refresh():
    uid = get_jwt_identity()
    new_access = create_access_token(identity=uid)
    return jsonify({"access_token": new_access}), 200

@auth_bp.get("/me")
@jwt_required()
def me():
    uid = get_jwt_identity()
    user = User.query.get(uid)
    if not user:
        return jsonify({"error": "user not found"}), 404
    return jsonify({"user": user.to_dict()}), 200

@auth_bp.post("/forgot")
def forgot_password():
    data = request.get_json(force=True, silent=True) or {}
    email = (data.get("email") or "").strip().lower()

   
    generic = {"message": "If the account exists, you will receive reset instructions shortly."}

    if not email:
        return jsonify(generic), 200

    user = User.query.filter_by(email=email).first()
    if user:
        expires = current_app.config.get("RESET_TOKEN_EXPIRES")
        reset_token = create_access_token(
            identity=user.id,
            additional_claims={"type": "reset"},
            expires_delta=expires
        )
        base = current_app.config.get("FRONTEND_URL", "http://localhost:5173")
        reset_link = f"{base}/reset-password?token={reset_token}"

        
        try:
            msg = Message(
                subject="Reset your Isuzu Local Pass password",
                recipients=[email],
            )
            msg.body = (
                f"Hi {user.full_name or ''}\n\n"
                "We received a request to reset your password.\n"
                f"Click the link below to set a new password (valid for {expires}):\n\n"
                f"{reset_link}\n\n"
                "If you didn’t request this, you can ignore this email."
            )
            
            msg.html = f"""
                <p>Hi {user.full_name or ''},</p>
                <p>We received a request to reset your password.</p>
                <p><a href="{reset_link}">Reset your password</a><br/>
                (This link is valid for {expires}.)</p>
                <p>If you didn’t request this, you can ignore this email.</p>
            """
            mail.send(msg)
        except Exception as e:
            print("[SMTP ERROR]", e)

    return jsonify(generic), 200
