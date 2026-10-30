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


def test_sqlite_chat_message_persistence():
    """Verifies that chat messages and sessions are stored in SQLite and can be retrieved."""
    user_id = f"user_chat_{int(time.time()*1000)}"
    proj_id = "test-project-alpha"
    session_id = auth_db.create_or_get_chat_session(user_id, proj_id, title="Test Architecture Chat")
    assert session_id.startswith("sess-")

    # Save user message
    msg1 = auth_db.save_chat_message(user_id, proj_id, session_id, role="user", content="Explain main.py please")
    assert msg1["id"].startswith("msg-")
    assert msg1["content"] == "Explain main.py please"

    # Save assistant reply
    msg2 = auth_db.save_chat_message(user_id, proj_id, session_id, role="assistant", content="main.py is the entrypoint.", sources=["main.py"])
    assert msg2["sources"] == ["main.py"]

    # Retrieve history
    history = auth_db.get_chat_history(user_id, proj_id, session_id)
    assert len(history) == 2
    assert history[0]["role"] == "user"
    assert history[1]["role"] == "assistant"

    # Verify sessions query
    sessions = auth_db.get_user_chat_sessions(user_id, proj_id)
    assert len(sessions) >= 1
    assert any(s["id"] == session_id for s in sessions)


def test_api_chat_endpoints_and_workspace_clean(monkeypatch):
    """Verifies REST endpoints for chat sessions, chat history, and workspace cleaning."""
    monkeypatch.setattr(server.ci_backend, "query_ollama_llm", lambda prompt: "Architecture summary: modular microservice.")
    email = f"chat_tester_{int(time.time()*1000)}@dev.local"
    r_signup = client.post("/api/auth/signup", json={
        "name": "Chat Engineer",
        "email": email,
        "password": "Password123",
        "confirmPassword": "Password123"
    })
    token = r_signup.json()["token"]

    # 1. Post a chat message
    r_chat = client.post("/api/project/chat",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "message": "What is the architecture?",
            "project_id": "proj-xyz",
            "context": {"project_name": "DemoApp", "structure": {"files": []}, "analysis": {"overview": "Demo"}}
        }
    )
    assert r_chat.status_code == 200
    res_data = r_chat.json()
    assert "reply" in res_data
    assert "session_id" in res_data
    session_id = res_data["session_id"]

    # 2. Get chat history
    r_hist = client.post if False else client.get(f"/api/project/chat/history?project_id=proj-xyz&session_id={session_id}",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert r_hist.status_code == 200
    msgs = r_hist.json()["messages"]
    assert len(msgs) >= 2  # user message and assistant reply

    # 3. Clean workspace endpoint
    r_clean = client.post("/api/workspace/clean",
        headers={"Authorization": f"Bearer {token}"},
        json={"project_id": "proj-xyz"}
    )
    assert r_clean.status_code == 200
    assert r_clean.json()["status"] == "success"

