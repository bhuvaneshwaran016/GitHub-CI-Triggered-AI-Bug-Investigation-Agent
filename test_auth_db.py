"""
Unit & Integration Tests for SQLite Authentication, Salted Password Hashing,
Forgot Password Token Lifecycles, and Password Change Workflows.
"""

import time
import pytest
from fastapi.testclient import TestClient

import auth_db
import server

client = TestClient(server.app)


def test_sqlite_user_creation_and_hashing():
    """Verifies user is stored in SQLite and password hash is salted and non-reversible."""
    email = f"test_{int(time.time()*1000)}@example.com"
    user = auth_db.create_user("Test Engineer", email, "SecurePass123!")

    assert user["name"] == "Test Engineer"
    assert user["email"] == email
    assert "password_hash" not in user
    assert "password" not in user

    # Directly inspect raw SQLite database row to confirm hash is salted
    with auth_db.get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT password_hash FROM users WHERE email = ?", (email,))
        row = cursor.fetchone()
        assert row is not None
        stored_hash = row["password_hash"]

        assert ":" in stored_hash, "Hash must have salt:key format"
        salt, key_hex = stored_hash.split(":")
        assert len(salt) == 32, "Salt must be 16-byte hex (32 chars)"
        assert len(key_hex) == 64, "Key must be 32-byte sha256 hex (64 chars)"
        assert stored_hash != "SecurePass123!", "Plaintext password must NEVER be in database"


def test_password_verification():
    """Verifies correct password passes and incorrect password fails."""
    email = f"verify_{int(time.time()*1000)}@example.com"
    auth_db.create_user("Bob", email, "secretPass99")

    # Correct password
    valid = auth_db.authenticate_user(email, "secretPass99")
    assert valid is not None
    assert valid["email"] == email

    # Wrong password
    invalid = auth_db.authenticate_user(email, "wrongPassword")
    assert invalid is None


def test_password_change():
    """Verifies user can change password by providing current password."""
    email = f"change_{int(time.time()*1000)}@example.com"
    user = auth_db.create_user("Charlie", email, "InitialPass123")

    # Fail with wrong old password
    failed = auth_db.change_user_password(user["id"], "wrongOldPass", "BrandNewPass456")
    assert failed is False

    # Succeed with correct old password
    success = auth_db.change_user_password(user["id"], "InitialPass123", "BrandNewPass456")
    assert success is True

    # Old password no longer works
    assert auth_db.authenticate_user(email, "InitialPass123") is None
    # New password works
    assert auth_db.authenticate_user(email, "BrandNewPass456") is not None


def test_forgot_and_reset_password_flow():
    """Verifies reset token generation and subsequent password reset."""
    email = f"reset_{int(time.time()*1000)}@example.com"
    auth_db.create_user("Dana", email, "OldPass2026")

    # Generate token
    token = auth_db.generate_password_reset_token(email)
    assert token is not None
    assert len(token) > 20

    # Reset with valid token
    success = auth_db.reset_password_with_token(token, "ResetPass2026!")
    assert success is True

    # Token cannot be reused (one-time use)
    reuse = auth_db.reset_password_with_token(token, "AnotherPass2026")
    assert reuse is False

    # Authenticate with new password
    auth_res = auth_db.authenticate_user(email, "ResetPass2026!")
    assert auth_res is not None


def test_api_auth_endpoints_end_to_end():
    """Verifies FastAPI REST endpoints for signup, signin, forgot, reset, and change password."""
    email = f"api_user_{int(time.time()*1000)}@dev.local"

    # 1. Sign up
    r_signup = client.post("/api/auth/signup", json={
        "name": "API Developer",
        "email": email,
        "password": "Password123",
        "confirmPassword": "Password123"
    })
    assert r_signup.status_code == 200
    token = r_signup.json()["token"]

    # 2. Sign in
    r_signin = client.post("/api/auth/signin", json={
        "email": email,
        "password": "Password123"
    })
    assert r_signin.status_code == 200
    assert r_signin.json()["user"]["email"] == email

    # 3. Change password with Bearer token
    r_change = client.post("/api/auth/change-password",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "oldPassword": "Password123",
            "newPassword": "UpdatedPassword456",
            "confirmPassword": "UpdatedPassword456"
        }
    )
    assert r_change.status_code == 200

    # 4. Forgot password
    r_forgot = client.post("/api/auth/forgot-password", json={"email": email})
    assert r_forgot.status_code == 200
    reset_tok = r_forgot.json()["token"]
    assert reset_tok is not None

    # 5. Reset password
    r_reset = client.post("/api/auth/reset-password", json={
        "token": reset_tok,
        "newPassword": "FinalPassword789",
        "confirmPassword": "FinalPassword789"
    })
    assert r_reset.status_code == 200

    # 6. Sign in with final password
    r_final = client.post("/api/auth/signin", json={
        "email": email,
        "password": "FinalPassword789"
    })
    assert r_final.status_code == 200

