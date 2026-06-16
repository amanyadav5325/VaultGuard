"""
VaultGuard - Encrypted Password Vault (SQLite3 backend)
Stores all passwords encrypted; only decrypts in-memory when needed.
"""

import os
import sqlite3
import json
from datetime import datetime
from typing import List, Optional, Dict, Any
from encryptor import encrypt_text, decrypt_text, get_or_create_salt, hash_master_password, verify_master_password

DB_PATH = os.path.join(os.path.dirname(__file__), "data", "vault.db")


def _get_conn() -> sqlite3.Connection:
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Create tables if they don't exist."""
    with _get_conn() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS master_auth (
                id INTEGER PRIMARY KEY,
                password_hash TEXT NOT NULL,
                salt_hex TEXT NOT NULL,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS vault_entries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                username TEXT,
                encrypted_password BLOB NOT NULL,
                url TEXT,
                category TEXT DEFAULT 'General',
                notes TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                last_rotated TEXT,
                rotation_interval_days INTEGER DEFAULT 90,
                strength_score INTEGER DEFAULT 0,
                is_active INTEGER DEFAULT 1
            );

            CREATE TABLE IF NOT EXISTS rotation_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                entry_id INTEGER NOT NULL,
                rotated_at TEXT NOT NULL,
                old_strength INTEGER,
                new_strength INTEGER,
                reason TEXT,
                FOREIGN KEY (entry_id) REFERENCES vault_entries(id)
            );
        """)


def is_vault_initialized() -> bool:
    init_db()
    with _get_conn() as conn:
        row = conn.execute("SELECT COUNT(*) as cnt FROM master_auth").fetchone()
        return row["cnt"] > 0


def setup_master_password(master_password: str) -> bool:
    """Set up the master password for the first time."""
    salt = get_or_create_salt()
    pw_hash = hash_master_password(master_password, salt)
    with _get_conn() as conn:
        conn.execute(
            "INSERT INTO master_auth (password_hash, salt_hex, created_at) VALUES (?, ?, ?)",
            (pw_hash, salt.hex(), datetime.now().isoformat())
        )
    return True


def unlock_vault(master_password: str) -> bool:
    """Verify master password. Returns True if correct."""
    with _get_conn() as conn:
        row = conn.execute("SELECT password_hash, salt_hex FROM master_auth LIMIT 1").fetchone()
        if not row:
            return False
        salt = bytes.fromhex(row["salt_hex"])
        return verify_master_password(master_password, row["password_hash"], salt)


def add_entry(master_password: str, title: str, username: str, password: str,
              url: str = "", category: str = "General", notes: str = "",
              rotation_interval: int = 90, strength_score: int = 0) -> int:
    """Add a new password entry to the vault."""
    encrypted_pw = encrypt_text(password, master_password)
    now = datetime.now().isoformat()
    with _get_conn() as conn:
        cur = conn.execute(
            """INSERT INTO vault_entries
               (title, username, encrypted_password, url, category, notes,
                created_at, updated_at, last_rotated, rotation_interval_days, strength_score)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (title, username, encrypted_pw, url, category, notes,
             now, now, now, rotation_interval, strength_score)
        )
        return cur.lastrowid


def get_all_entries(master_password: str) -> List[Dict[str, Any]]:
    """Retrieve and decrypt all active vault entries."""
    with _get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM vault_entries WHERE is_active=1 ORDER BY category, title"
        ).fetchall()

    results = []
    for row in rows:
        try:
            decrypted_pw = decrypt_text(row["encrypted_password"], master_password)
        except Exception:
            decrypted_pw = "⚠ Decryption failed"
        entry = dict(row)
        entry["password"] = decrypted_pw
        results.append(entry)
    return results


def get_entry(master_password: str, entry_id: int) -> Optional[Dict[str, Any]]:
    """Retrieve and decrypt a single entry."""
    with _get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM vault_entries WHERE id=? AND is_active=1", (entry_id,)
        ).fetchone()
    if not row:
        return None
    entry = dict(row)
    entry["password"] = decrypt_text(row["encrypted_password"], master_password)
    return entry


def update_entry(master_password: str, entry_id: int, **kwargs) -> bool:
    """Update a vault entry. Pass new password in kwargs to re-encrypt."""
    if "password" in kwargs:
        kwargs["encrypted_password"] = encrypt_text(kwargs.pop("password"), master_password)
    kwargs["updated_at"] = datetime.now().isoformat()

    set_clause = ", ".join(f"{k}=?" for k in kwargs)
    values = list(kwargs.values()) + [entry_id]
    with _get_conn() as conn:
        conn.execute(f"UPDATE vault_entries SET {set_clause} WHERE id=?", values)
    return True


def delete_entry(entry_id: int) -> bool:
    """Soft-delete a vault entry."""
    with _get_conn() as conn:
        conn.execute("UPDATE vault_entries SET is_active=0 WHERE id=?", (entry_id,))
    return True


def rotate_password(master_password: str, entry_id: int, new_password: str,
                    new_strength: int, reason: str = "Manual rotation") -> bool:
    """Rotate a password and log the event."""
    entry = get_entry(master_password, entry_id)
    if not entry:
        return False

    old_strength = entry.get("strength_score", 0)
    now = datetime.now().isoformat()
    encrypted_new = encrypt_text(new_password, master_password)

    with _get_conn() as conn:
        conn.execute(
            """UPDATE vault_entries
               SET encrypted_password=?, strength_score=?, last_rotated=?, updated_at=?
               WHERE id=?""",
            (encrypted_new, new_strength, now, now, entry_id)
        )
        conn.execute(
            """INSERT INTO rotation_log (entry_id, rotated_at, old_strength, new_strength, reason)
               VALUES (?, ?, ?, ?, ?)""",
            (entry_id, now, old_strength, new_strength, reason)
        )
    return True


def get_entries_due_for_rotation() -> List[Dict[str, Any]]:
    """Return entries whose passwords are overdue for rotation."""
    with _get_conn() as conn:
        rows = conn.execute(
            """SELECT *, 
               julianday('now') - julianday(last_rotated) AS days_since_rotation
               FROM vault_entries
               WHERE is_active=1
               AND (julianday('now') - julianday(last_rotated)) >= rotation_interval_days"""
        ).fetchall()
    return [dict(r) for r in rows]


def get_rotation_log(entry_id: Optional[int] = None) -> List[Dict[str, Any]]:
    """Get rotation history."""
    with _get_conn() as conn:
        if entry_id:
            rows = conn.execute(
                """SELECT r.*, v.title FROM rotation_log r
                   JOIN vault_entries v ON r.entry_id=v.id
                   WHERE r.entry_id=? ORDER BY r.rotated_at DESC""",
                (entry_id,)
            ).fetchall()
        else:
            rows = conn.execute(
                """SELECT r.*, v.title FROM rotation_log r
                   JOIN vault_entries v ON r.entry_id=v.id
                   ORDER BY r.rotated_at DESC LIMIT 100"""
            ).fetchall()
    return [dict(r) for r in rows]


def get_vault_stats() -> Dict[str, Any]:
    """Get summary statistics for the dashboard."""
    with _get_conn() as conn:
        total = conn.execute("SELECT COUNT(*) FROM vault_entries WHERE is_active=1").fetchone()[0]
        weak = conn.execute("SELECT COUNT(*) FROM vault_entries WHERE is_active=1 AND strength_score < 40").fetchone()[0]
        fair = conn.execute("SELECT COUNT(*) FROM vault_entries WHERE is_active=1 AND strength_score >= 40 AND strength_score < 65").fetchone()[0]
        strong = conn.execute("SELECT COUNT(*) FROM vault_entries WHERE is_active=1 AND strength_score >= 65").fetchone()[0]
        overdue = conn.execute(
            """SELECT COUNT(*) FROM vault_entries WHERE is_active=1
               AND (julianday('now') - julianday(last_rotated)) >= rotation_interval_days"""
        ).fetchone()[0]
        categories = conn.execute(
            "SELECT category, COUNT(*) as cnt FROM vault_entries WHERE is_active=1 GROUP BY category"
        ).fetchall()

    return {
        "total": total,
        "weak": weak,
        "fair": fair,
        "strong": strong,
        "overdue_rotation": overdue,
        "categories": {r["category"]: r["cnt"] for r in categories}
    }
