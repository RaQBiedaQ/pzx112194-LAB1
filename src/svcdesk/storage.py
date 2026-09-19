# ai-generated: 90% - Claude (AI assistant) generated this module under the student's direction (decisions, review, testing)
"""SQLite-backed ticket storage. Tickets are stored as JSON blobs keyed by id: the desk is small
(REQUIREMENTS.md R-19), so a single table with in-Python filtering is enough, and it keeps the
schema stable while the ticket shape (API.md section 2) evolves across labs (R-23)."""
import json
import sqlite3
import threading
from typing import Optional

from . import config

_lock = threading.Lock()
_conn: Optional[sqlite3.Connection] = None


def _connection() -> sqlite3.Connection:
    global _conn
    if _conn is None:
        path = config.db_path()
        _conn = sqlite3.connect(path, check_same_thread=False)
        _conn.execute(
            "CREATE TABLE IF NOT EXISTS tickets ("
            "id TEXT PRIMARY KEY, "
            "created_at TEXT NOT NULL, "
            "data TEXT NOT NULL"
            ")"
        )
        _conn.commit()
    return _conn


def reset_connection_for_tests() -> None:
    """Not used at runtime; here so a future test suite can point at a fresh file if needed."""
    global _conn
    with _lock:
        if _conn is not None:
            _conn.close()
        _conn = None


def insert(ticket: dict) -> None:
    with _lock:
        conn = _connection()
        conn.execute(
            "INSERT INTO tickets (id, created_at, data) VALUES (?, ?, ?)",
            (ticket["id"], ticket["created_at"], json.dumps(ticket)),
        )
        conn.commit()


def update(ticket: dict) -> None:
    with _lock:
        conn = _connection()
        conn.execute(
            "UPDATE tickets SET data = ? WHERE id = ?",
            (json.dumps(ticket), ticket["id"]),
        )
        conn.commit()


def get(ticket_id: str) -> Optional[dict]:
    with _lock:
        conn = _connection()
        row = conn.execute("SELECT data FROM tickets WHERE id = ?", (ticket_id,)).fetchone()
        return json.loads(row[0]) if row else None


def list_all(state: Optional[str] = None, priority: Optional[str] = None) -> list[dict]:
    with _lock:
        conn = _connection()
        rows = conn.execute("SELECT data FROM tickets ORDER BY created_at").fetchall()
    tickets = [json.loads(r[0]) for r in rows]
    if state is not None:
        tickets = [t for t in tickets if t["state"] == state]
    if priority is not None:
        tickets = [t for t in tickets if t["priority"] == priority]
    return tickets
