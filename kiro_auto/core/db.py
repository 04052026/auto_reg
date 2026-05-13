"""SQLite database for storing accounts and task logs."""

import json
import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, List

from core.config import DEFAULT_DB_PATH


_db_lock = threading.Lock()
_db_path: str = str(DEFAULT_DB_PATH)


def _get_connection() -> sqlite3.Connection:
    """Get a new SQLite connection. Caller must close it."""
    conn = sqlite3.connect(_db_path, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db(db_path: Optional[str] = None):
    """Initialize database schema."""
    global _db_path
    if db_path:
        _db_path = db_path

    Path(_db_path).parent.mkdir(parents=True, exist_ok=True)

    with _get_connection() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS accounts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT NOT NULL,
                password TEXT NOT NULL,
                status TEXT DEFAULT 'registered',
                access_token TEXT DEFAULT '',
                refresh_token TEXT DEFAULT '',
                client_id TEXT DEFAULT '',
                client_secret TEXT DEFAULT '',
                client_id_hash TEXT DEFAULT '',
                session_token TEXT DEFAULT '',
                web_access_token TEXT DEFAULT '',
                region TEXT DEFAULT 'us-east-1',
                extra_json TEXT DEFAULT '{}',
                email_provider TEXT DEFAULT '',
                created_at TEXT DEFAULT (datetime('now')),
                updated_at TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS task_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT DEFAULT '',
                status TEXT NOT NULL,
                error TEXT DEFAULT '',
                email_provider TEXT DEFAULT '',
                duration_seconds REAL DEFAULT 0,
                created_at TEXT DEFAULT (datetime('now'))
            );

            CREATE INDEX IF NOT EXISTS idx_accounts_email ON accounts(email);
            CREATE INDEX IF NOT EXISTS idx_accounts_status ON accounts(status);
            CREATE INDEX IF NOT EXISTS idx_task_logs_status ON task_logs(status);
        """)


def save_account(
    email: str,
    password: str,
    tokens: dict,
    email_provider: str = "",
    status: str = "registered",
) -> int:
    """Save a newly registered account. Returns the account ID."""
    with _db_lock:
        with _get_connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO accounts (
                    email, password, status, access_token, refresh_token,
                    client_id, client_secret, client_id_hash, session_token,
                    web_access_token, region, extra_json, email_provider
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    email,
                    password,
                    status,
                    tokens.get("accessToken", ""),
                    tokens.get("refreshToken", ""),
                    tokens.get("clientId", ""),
                    tokens.get("clientSecret", ""),
                    tokens.get("clientIdHash", ""),
                    tokens.get("sessionToken", ""),
                    tokens.get("webAccessToken", ""),
                    tokens.get("region", "us-east-1"),
                    json.dumps(tokens, ensure_ascii=False),
                    email_provider,
                ),
            )
            return cursor.lastrowid


def get_account(account_id: int) -> Optional[dict]:
    """Get account by ID."""
    conn = _get_connection()
    try:
        row = conn.execute("SELECT * FROM accounts WHERE id = ?", (account_id,)).fetchone()
        if row:
            return dict(row)
    finally:
        conn.close()
    return None


def get_latest_account() -> Optional[dict]:
    """Get the most recently created account."""
    conn = _get_connection()
    try:
        row = conn.execute(
            "SELECT * FROM accounts ORDER BY id DESC LIMIT 1"
        ).fetchone()
        if row:
            return dict(row)
    finally:
        conn.close()
    return None


def list_accounts(status: Optional[str] = None, limit: int = 100) -> List[dict]:
    """List all accounts, optionally filtered by status."""
    conn = _get_connection()
    try:
        if status:
            rows = conn.execute(
                "SELECT * FROM accounts WHERE status = ? ORDER BY id DESC LIMIT ?",
                (status, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM accounts ORDER BY id DESC LIMIT ?", (limit,)
            ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def update_account_tokens(account_id: int, tokens: dict):
    """Update tokens for an account."""
    with _db_lock:
        with _get_connection() as conn:
            conn.execute(
                """
                UPDATE accounts SET
                    access_token = ?,
                    refresh_token = ?,
                    extra_json = ?,
                    updated_at = datetime('now')
                WHERE id = ?
                """,
                (
                    tokens.get("accessToken", ""),
                    tokens.get("refreshToken", ""),
                    json.dumps(tokens, ensure_ascii=False),
                    account_id,
                ),
            )


def update_account_status(account_id: int, status: str):
    """Update account status."""
    with _db_lock:
        with _get_connection() as conn:
            conn.execute(
                "UPDATE accounts SET status = ?, updated_at = datetime('now') WHERE id = ?",
                (status, account_id),
            )


def save_task_log(
    email: str, status: str, error: str = "",
    email_provider: str = "", duration: float = 0,
):
    """Save a task execution log."""
    with _db_lock:
        with _get_connection() as conn:
            conn.execute(
                """
                INSERT INTO task_logs (email, status, error, email_provider, duration_seconds)
                VALUES (?, ?, ?, ?, ?)
                """,
                (email, status, error, email_provider, duration),
            )


def get_stats() -> dict:
    """Get summary statistics."""
    conn = _get_connection()
    try:
        total = conn.execute("SELECT COUNT(*) FROM accounts").fetchone()[0]
        active = conn.execute(
            "SELECT COUNT(*) FROM accounts WHERE status = 'registered'"
        ).fetchone()[0]
        expired = conn.execute(
            "SELECT COUNT(*) FROM accounts WHERE status = 'expired'"
        ).fetchone()[0]
        last_row = conn.execute(
            "SELECT created_at FROM accounts ORDER BY id DESC LIMIT 1"
        ).fetchone()
        last_created = last_row[0] if last_row else "Never"
    finally:
        conn.close()

    return {
        "total": total,
        "active": active,
        "expired": expired,
        "last_created": last_created,
    }
