
"""
Unit Tests for Authentication, Password Hashing, and JWT/HMAC Tokens
"""

import pytest

from app.auth import generate_token, verify_token, authenticate_user
from app.models import hash_password, init_db


def test_hash_password_consistency():
    pwd = "SecurePassword@2026"
    h1 = hash_password(pwd)
    h2 = hash_password(pwd)

    assert h1 == h2
    assert len(h1) == 64


def test_hash_password_different_inputs():
    h1 = hash_password("pass1")
    h2 = hash_password("pass2")

    assert h1 != h2


def test_generate_and_verify_valid_token():
    token = generate_token(
        user_id=42,
        username="test_engineer",
        role="tester",
        expires_in=3600
    )

    assert isinstance(token, str)
    assert len(token.split(".")) == 3

    payload, err = verify_token(token)

    assert err is None
    assert payload["sub"] == 42
    assert payload["username"] == "test_engineer"
    assert payload["role"] == "tester"


def test_token_expiration():
    token = generate_token(
        user_id=1,
        username="admin",
        role="admin",
        expires_in=-10
    )

    payload, err = verify_token(token)

    assert payload is None
    assert "expired" in err.lower()


def test_tampered_token_signature():
    token = generate_token(
        user_id=1,
        username="admin",
        role="admin"
    )

    parts = token.split(".")
    tampered_token = f"{parts[0]}.{parts[1]}.tamperedSignature123"

    payload, err = verify_token(tampered_token)

    assert payload is None
    assert "mismatch" in err.lower() or "signature" in err.lower()


def test_malformed_token():
    payload, err = verify_token("not-a-real-token")

    assert payload is None
    assert "invalid token format" in err.lower()


def test_corrupted_token_returns_error():
    token = "eyJhbGciOiJIUzI1NiJ9.@@@invalid@@@.c2ln"

    payload, err = verify_token(token)

    assert payload is None
    assert err is not None


def test_authenticate_user_invalid_credentials(test_db_path):
    # Initialize an isolated database before authentication.
    init_db(test_db_path)

    user = authenticate_user(
        username="nonexistent_user_123",
        password="WrongPassword@123",
        db_path=test_db_path
    )

    assert user is None
