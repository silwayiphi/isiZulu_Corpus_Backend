# auth.py
from datetime import timedelta
from flask import Blueprint, request, jsonify, current_app
from flask_mail import Message
from sqlalchemy.exc import IntegrityError

from extensions import db, mail
from models import User
from threading import Thread
from flask import current_app

from flask_jwt_extended import (
    create_access_token,
    create_refresh_token,
    jwt_required,
    get_jwt_identity,
    decode_token,
)

auth_bp = Blueprint("auth", __name__, url_prefix="/auth")


def _frontend_base_url():
    fe = current_app.config.get("FRONTEND_BASE_URL") or current_app.config.get("FRONTEND_URL")
    if fe: return fe.rstrip("/")
    origin = request.headers.get("Origin")
    if origin: return origin.rstrip("/")
    return "http://localhost:3000"

def _friendly_exp(expires) -> str:
    """Turn timedelta into a friendly string for the email."""
    if isinstance(expires, timedelta):
        total = int(expires.total_seconds())
        hours = total // 3600
        minutes = (total % 3600) // 60
        if hours and minutes:
            return f"{hours}h {minutes}m"
        if hours:
            return f"{hours} hour" + ("s" if hours != 1 else "")
        return f"{minutes} minutes"
    return "60 minutes"



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
    """
    Explicit UX:
      - known email   -> 200 {message}
      - unknown email -> 404 {error, action:'signup', signup_url}
    """
    data = request.get_json(force=True, silent=True) or {}
    email = (data.get("email") or "").strip().lower()
    if not email:
        return jsonify({"error": "email required"}), 400

    user = User.query.filter_by(email=email).first()
    if not user:
        return jsonify({
            "error": "Email not registered. Please create an account.",
            "action": "signup",
            "signup_url": f"{_frontend_base_url()}/signup"
        }), 404

    expires = current_app.config.get("RESET_TOKEN_EXPIRES", timedelta(hours=1))
    token = create_access_token(identity=user.id,
                                additional_claims={"type": "reset"},
                                expires_delta=expires)

    reset_link = f"{_frontend_base_url()}/reset?token={token}"

    try:
        msg = Message(subject="Reset your password", recipients=[email])
        msg.body = (
            f"Hi {user.full_name or ''}\n\n"
            "We received a request to reset your password.\n"
            f"Use this link (valid for 60 minutes):\n{reset_link}\n\n"
            "If you didn’t request this, you can ignore this email."
        )
        msg.html = (
            f"<p>Hi {user.full_name or ''},</p>"
            "<p>We received a request to reset your password.</p>"
            f'<p><a href="{reset_link}">Reset your password</a> (valid for 60 minutes).</p>'
            "<p>If you didn’t request this, you can ignore this email.</p>"
        )
        mail.send(msg)
    except Exception as e:
        current_app.logger.exception("SMTP error sending reset email: %s", e)

    return jsonify({"message": "User registered, Reset link sent to your email."}), 200


@auth_bp.post("/reset")
def reset_password():
    """
    Body: { token, password }
    """
    data = request.get_json(force=True, silent=True) or {}
    token = (data.get("token") or "").strip()
    new_pw = data.get("password") or ""
    if not token or not new_pw:
        return jsonify({"error": "token and password required"}), 400
    if len(new_pw) < 6:
        return jsonify({"error": "password must be at least 6 characters"}), 400

    try:
        decoded = decode_token(token)  # raises if invalid/expired
    except Exception:
        return jsonify({"error": "invalid or expired reset link"}), 400

    if decoded.get("type") != "reset":
        return jsonify({"error": "invalid reset token"}), 400

    uid = decoded.get("sub") or decoded.get("identity")
    user = User.query.get(uid)
    if not user:
        return jsonify({"error": "user not found"}), 404

    user.set_password(new_pw)
    db.session.commit()
    return jsonify({"message": "Password updated successfully."}), 200