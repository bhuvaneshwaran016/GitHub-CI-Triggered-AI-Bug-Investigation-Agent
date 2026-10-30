"""
SQLite Authentication & Secure User Database Module
Provides cryptographically secure salted password hashing (PBKDF2-HMAC-SHA256),
safe SQLite storage, password reset token management, and password change operations.
No plaintext passwords are ever persisted or exposed.
"""

import hashlib
import json
import os
import secrets
import sqlite3
import time
import uuid
from pathlib import Path
from typing import Optional, Dict, Any, List

DB_PATH = Path(__file__).resolve().parent / "users.db"


def get_db_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Initializes SQLite schema and creates the users, chat_sessions, and chat_messages tables if not exists."""
    with get_db_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                reset_token TEXT,
                reset_token_expiry REAL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_users_reset_token ON users(reset_token);")

        # Chat Sessions & Messages Tables for Persistent SQLite Chat History
        conn.execute("""
            CREATE TABLE IF NOT EXISTS chat_sessions (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                project_id TEXT NOT NULL,
                title TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_chat_sessions_user ON chat_sessions(user_id, project_id);")

        conn.execute("""
            CREATE TABLE IF NOT EXISTS chat_messages (
                id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                user_id TEXT NOT NULL,
                project_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                sources_json TEXT,
                created_at TEXT NOT NULL
            );
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_chat_messages_session ON chat_messages(session_id, created_at);")
        conn.commit()

        # Seed default engineer account if empty
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM users")
        if cursor.fetchone()[0] == 0:
            default_salt = secrets.token_hex(16)
            default_key = hashlib.pbkdf2_hmac('sha256', 'projectdemo2026'.encode('utf-8'), default_salt.encode('utf-8'), 100_000)
            default_hash = f"{default_salt}:{default_key.hex()}"
            now_iso = time.strftime("%Y-%m-%d %H:%M:%S")
            cursor.execute("""
                INSERT INTO users (id, name, email, password_hash, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, ("user-demo-lead", "Lead Engineer", "lead.engineer@taskflow.dev", default_hash, now_iso, now_iso))
            conn.commit()


def hash_password(password: str) -> str:
    """Hashes password with 16-byte random salt and 100,000 PBKDF2 iterations."""
    salt = secrets.token_hex(16)
    key = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt.encode('utf-8'), 100_000)
    return f"{salt}:{key.hex()}"


def verify_password(stored_password_hash: str, provided_password: str) -> bool:
    """Verifies candidate password against stored salt and PBKDF2 hash using constant-time comparison."""
    try:
        salt, key_hex = stored_password_hash.split(":")
        new_key = hashlib.pbkdf2_hmac('sha256', provided_password.encode('utf-8'), salt.encode('utf-8'), 100_000)
        return secrets.compare_digest(new_key.hex(), key_hex)
    except Exception:
        return False


def create_user(name: str, email: str, password: str) -> Dict[str, Any]:
    """Creates a new user record with hashed password."""
    clean_name = name.strip()
    clean_email = email.strip().lower()

    if not clean_name:
        raise ValueError("Name cannot be empty")
    if not clean_email or "@" not in clean_email:
        raise ValueError("Valid email address is required")
    if len(password) < 6:
        raise ValueError("Password must be at least 6 characters long")

    p_hash = hash_password(password)
    user_id = f"user-{uuid.uuid4().hex[:10]}"
    now_str = time.strftime("%Y-%m-%d %H:%M:%S")

    try:
        with get_db_connection() as conn:
            conn.execute("""
                INSERT INTO users (id, name, email, password_hash, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (user_id, clean_name, clean_email, p_hash, now_str, now_str))
            conn.commit()
    except sqlite3.IntegrityError:
        raise ValueError("An account with this email address already exists.")

    return {
        "id": user_id,
        "name": clean_name,
        "email": clean_email,
        "created_at": now_str,
    }


def authenticate_user(email: str, password: str) -> Optional[Dict[str, Any]]:
    """Authenticates email and password. Returns user dict (without password_hash) if successful."""
    clean_email = email.strip().lower()
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, name, email, password_hash, created_at FROM users WHERE email = ?", (clean_email,))
        row = cursor.fetchone()
        if not row:
            return None

        if verify_password(row["password_hash"], password):
            return {
                "id": row["id"],
                "name": row["name"],
                "email": row["email"],
                "created_at": row["created_at"],
            }
        return None


def get_user_by_id(user_id: str) -> Optional[Dict[str, Any]]:
    """Retrieves user by ID without revealing password hash."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, name, email, created_at FROM users WHERE id = ?", (user_id,))
        row = cursor.fetchone()
        if not row:
            return None
        return dict(row)


def generate_password_reset_token(email: str) -> Optional[str]:
    """Generates a secure 32-byte reset token valid for 1 hour."""
    clean_email = email.strip().lower()
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM users WHERE email = ?", (clean_email,))
        row = cursor.fetchone()
        if not row:
            return None

        token = secrets.token_urlsafe(32)
        expiry = time.time() + 3600  # 1 hour from now
        now_str = time.strftime("%Y-%m-%d %H:%M:%S")

        cursor.execute("""
            UPDATE users
            SET reset_token = ?, reset_token_expiry = ?, updated_at = ?
            WHERE email = ?
        """, (token, expiry, now_str, clean_email))
        conn.commit()
        return token


def reset_password_with_token(token: str, new_password: str) -> bool:
    """Verifies the reset token, updates to new hashed password, and clears token."""
    if len(new_password) < 6:
        raise ValueError("Password must be at least 6 characters long")

    clean_token = token.strip()
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, reset_token_expiry FROM users
            WHERE reset_token = ?
        """, (clean_token,))
        row = cursor.fetchone()

        if not row:
            return False

        if row["reset_token_expiry"] < time.time():
            # Expired token
            return False

        new_hash = hash_password(new_password)
        now_str = time.strftime("%Y-%m-%d %H:%M:%S")

        cursor.execute("""
            UPDATE users
            SET password_hash = ?, reset_token = NULL, reset_token_expiry = NULL, updated_at = ?
            WHERE id = ?
        """, (new_hash, now_str, row["id"]))
        conn.commit()
        return True


def change_user_password(user_id: str, old_password: str, new_password: str) -> bool:
    """Allows an authenticated user to change password after verifying old password."""
    if len(new_password) < 6:
        raise ValueError("New password must be at least 6 characters long")

    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, password_hash FROM users WHERE id = ?", (user_id,))
        row = cursor.fetchone()

        if not row:
            return False

        if not verify_password(row["password_hash"], old_password):
            return False

        new_hash = hash_password(new_password)
        now_str = time.strftime("%Y-%m-%d %H:%M:%S")

        cursor.execute("""
            UPDATE users
            SET password_hash = ?, updated_at = ?
            WHERE id = ?
        """, (new_hash, now_str, user_id))
        conn.commit()
        return True


# ==========================================================================
# Chat Sessions & Persistent History Storage
# ==========================================================================
def create_or_get_chat_session(user_id: str, project_id: str, session_id: Optional[str] = None, title: Optional[str] = None) -> str:
    now_str = time.strftime("%Y-%m-%d %H:%M:%S")
    with get_db_connection() as conn:
        cursor = conn.cursor()
        if session_id:
            cursor.execute("SELECT id FROM chat_sessions WHERE id = ? AND user_id = ?", (session_id, user_id))
            row = cursor.fetchone()
            if row:
                return row["id"]

        new_session_id = session_id or f"sess-{uuid.uuid4().hex[:12]}"
        sess_title = title or "New Architecture Chat"
        cursor.execute("""
            INSERT OR IGNORE INTO chat_sessions (id, user_id, project_id, title, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (new_session_id, user_id, project_id, sess_title, now_str, now_str))
        conn.commit()
        return new_session_id


def save_chat_message(user_id: str, project_id: str, session_id: str, role: str, content: str, sources: Optional[List[str]] = None) -> Dict[str, Any]:
    sess_id = create_or_get_chat_session(user_id, project_id, session_id)
    msg_id = f"msg-{uuid.uuid4().hex[:12]}"
    now_str = time.strftime("%Y-%m-%d %H:%M:%S")
    sources_json = json.dumps(sources or [])

    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO chat_messages (id, session_id, user_id, project_id, role, content, sources_json, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (msg_id, sess_id, user_id, project_id, role, content, sources_json, now_str))

        # Update session title if user message and first message
        if role == "user":
            cursor.execute("SELECT COUNT(*) FROM chat_messages WHERE session_id = ?", (sess_id,))
            msg_count = cursor.fetchone()[0]
            if msg_count <= 2:
                cleaned_title = content.strip().split("\n")[0][:45]
                cursor.execute("""
                    UPDATE chat_sessions
                    SET title = ?, updated_at = ?
                    WHERE id = ? AND (title = 'New Architecture Chat' OR title = 'New Conversation')
                """, (cleaned_title, now_str, sess_id))
            else:
                cursor.execute("UPDATE chat_sessions SET updated_at = ? WHERE id = ?", (now_str, sess_id))
        else:
            cursor.execute("UPDATE chat_sessions SET updated_at = ? WHERE id = ?", (now_str, sess_id))

        conn.commit()

    return {
        "id": msg_id,
        "session_id": sess_id,
        "user_id": user_id,
        "project_id": project_id,
        "role": role,
        "content": content,
        "sources": sources or [],
        "created_at": now_str,
    }


def get_chat_history(user_id: str, project_id: str, session_id: Optional[str] = None) -> List[Dict[str, Any]]:
    with get_db_connection() as conn:
        cursor = conn.cursor()
        if session_id:
            cursor.execute("""
                SELECT id, session_id, user_id, project_id, role, content, sources_json, created_at
                FROM chat_messages
                WHERE user_id = ? AND session_id = ?
                ORDER BY rowid ASC
            """, (user_id, session_id))
        else:
            cursor.execute("""
                SELECT id FROM chat_sessions
                WHERE user_id = ? AND project_id = ?
                ORDER BY updated_at DESC LIMIT 1
            """, (user_id, project_id))
            row = cursor.fetchone()
            if not row:
                return []
            latest_sess = row["id"]
            cursor.execute("""
                SELECT id, session_id, user_id, project_id, role, content, sources_json, created_at
                FROM chat_messages
                WHERE user_id = ? AND session_id = ?
                ORDER BY rowid ASC
            """, (user_id, latest_sess))

        rows = cursor.fetchall()
        result = []
        for r in rows:
            sources = []
            if r["sources_json"]:
                try:
                    sources = json.loads(r["sources_json"])
                except Exception:
                    pass
            result.append({
                "id": r["id"],
                "session_id": r["session_id"],
                "user_id": r["user_id"],
                "project_id": r["project_id"],
                "role": r["role"],
                "content": r["content"],
                "sources": sources,
                "created_at": r["created_at"],
            })
        return result


def get_user_chat_sessions(user_id: str, project_id: str) -> List[Dict[str, Any]]:
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT s.id, s.title, s.created_at, s.updated_at,
                   COUNT(m.id) as message_count
            FROM chat_sessions s
            LEFT JOIN chat_messages m ON s.id = m.session_id
            WHERE s.user_id = ? AND s.project_id = ?
            GROUP BY s.id
            ORDER BY s.updated_at DESC
        """, (user_id, project_id))
        rows = cursor.fetchall()
        return [dict(r) for r in rows]


def delete_chat_session(user_id: str, session_id: str) -> bool:
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM chat_messages WHERE user_id = ? AND session_id = ?", (user_id, session_id))
        cursor.execute("DELETE FROM chat_sessions WHERE user_id = ? AND id = ?", (user_id, session_id))
        conn.commit()
        return cursor.rowcount > 0


def clear_project_chat(user_id: str, project_id: str) -> bool:
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM chat_messages WHERE user_id = ? AND project_id = ?", (user_id, project_id))
        cursor.execute("DELETE FROM chat_sessions WHERE user_id = ? AND project_id = ?", (user_id, project_id))
        conn.commit()
        return True


def clear_all_user_chats(user_id: Optional[str] = None) -> bool:
    with get_db_connection() as conn:
        cursor = conn.cursor()
        if user_id:
            cursor.execute("DELETE FROM chat_messages WHERE user_id = ?", (user_id,))
            cursor.execute("DELETE FROM chat_sessions WHERE user_id = ?", (user_id,))
        else:
            cursor.execute("DELETE FROM chat_messages")
            cursor.execute("DELETE FROM chat_sessions")
        conn.commit()
        return True


# Auto-initialize DB on import
init_db()

