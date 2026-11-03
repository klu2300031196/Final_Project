"""
Authentication & Authorization Module (JWT / HMAC Bearer Token)
"""
import hmac
import hashlib
import base64
import json
import time
from functools import wraps
from flask import request, jsonify, current_app, has_request_context
from app.models import get_connection, hash_password

SECRET_KEY = "devops-testing-framework-super-secure-key-2026"

def generate_token(user_id: int, username: str, role: str, expires_in: int = 3600) -> str:
    """Generate a lightweight HMAC-SHA256 Signed Bearer Token."""
    header = {"alg": "HS256", "typ": "JWT"}
    payload = {
        "sub": user_id,
        "username": username,
        "role": role,
        "iat": int(time.time()),
        "exp": int(time.time()) + expires_in
    }

    h_b64 = base64.urlsafe_b64encode(json.dumps(header).encode()).decode().rstrip("=")
    p_b64 = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip("=")
    signature = hmac.new(SECRET_KEY.encode(), f"{h_b64}.{p_b64}".encode(), hashlib.sha256).digest()
    s_b64 = base64.urlsafe_b64encode(signature).decode().rstrip("=")

    return f"{h_b64}.{p_b64}.{s_b64}"

def verify_token(token: str):
    """Verify and decode HMAC-SHA256 token."""
    try:
        parts = token.strip().split(".")
        if len(parts) != 3:
            return None, "Invalid token format"

        h_b64, p_b64, s_b64 = parts
        expected_sig = hmac.new(SECRET_KEY.encode(), f"{h_b64}.{p_b64}".encode(), hashlib.sha256).digest()
        actual_sig = base64.urlsafe_b64decode(s_b64 + "==")

        if not hmac.compare_digest(expected_sig, actual_sig):
            return None, "Signature mismatch"

        payload_bytes = base64.urlsafe_b64decode(p_b64 + "==")
        payload = json.loads(payload_bytes.decode())

        if payload.get("exp") and payload["exp"] < time.time():
            return None, "Token expired"

        return payload, None
    except Exception as e:
        return None, str(e)

def authenticate_user(username, password, db_path=None):
    """Check credentials against database and return user record if valid."""
    if not db_path and has_request_context():
        db_path = current_app.config.get("DB_PATH")
    conn = get_connection(db_path)
    cur = conn.cursor()
    pwd_hash = hash_password(password)
    cur.execute("SELECT id, username, email, role FROM users WHERE username = ? AND password_hash = ?", (username, pwd_hash))
    user = cur.fetchone()
    conn.close()
    if user:
        return dict(user)
    return None

def login_required(roles=None):
    """Flask decorator for endpoint route protection."""
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            auth_header = request.headers.get("Authorization", "")
            if not auth_header.startswith("Bearer "):
                return jsonify({"error": "Missing or invalid Authorization header", "code": 401}), 401

            token = auth_header.split(" ", 1)[1]
            payload, err = verify_token(token)
            if err:
                return jsonify({"error": f"Unauthorized: {err}", "code": 401}), 401

            if roles and payload.get("role") not in roles:
                return jsonify({"error": "Forbidden: insufficient permissions", "code": 403}), 403

            request.current_user = payload
            return f(*args, **kwargs)
        return wrapper
    return decorator
