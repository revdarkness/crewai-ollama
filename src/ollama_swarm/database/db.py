"""
SQLite Database for Teaching Assistant Crew.

Tables:
- nudges: Reminders and action items
- notes: Unstructured observations
- sent_log: Email/SMS audit trail
- email_ingest_log: Processed trigger emails
"""

import sqlite3
import os
from datetime import datetime
from typing import Optional, List, Dict, Any
from contextlib import contextmanager


class Database:
    """SQLite database manager for Teaching Assistant."""

    def __init__(self, db_path: str = None):
        """Initialize database connection."""
        self.db_path = db_path or os.getenv("DB_PATH", "teacher_assistant.db")
        self._ensure_tables()

    @contextmanager
    def _get_connection(self):
        """Context manager for database connections."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _ensure_tables(self):
        """Create tables if they don't exist."""
        with self._get_connection() as conn:
            cursor = conn.cursor()

            # Nudges table - reminders and action items
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS nudges (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    content TEXT NOT NULL,
                    due_datetime TEXT,
                    priority TEXT DEFAULT 'normal',
                    status TEXT DEFAULT 'pending',
                    source TEXT DEFAULT 'manual',
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    completed_at TEXT,
                    CONSTRAINT valid_priority CHECK (priority IN ('low', 'normal', 'high', 'urgent')),
                    CONSTRAINT valid_status CHECK (status IN ('pending', 'sent', 'completed', 'cancelled'))
                )
            """)

            # Notes table - unstructured observations
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS notes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    content TEXT NOT NULL,
                    tags TEXT,
                    source TEXT DEFAULT 'manual',
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Sent log - email/SMS audit trail
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS sent_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    channel TEXT NOT NULL,
                    recipient TEXT NOT NULL,
                    subject TEXT,
                    content TEXT NOT NULL,
                    status TEXT DEFAULT 'sent',
                    sent_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    error_message TEXT,
                    CONSTRAINT valid_channel CHECK (channel IN ('email', 'sms'))
                )
            """)

            # Email ingest log - processed trigger emails
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS email_ingest_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    message_id TEXT UNIQUE NOT NULL,
                    subject TEXT,
                    sender TEXT,
                    command_type TEXT,
                    command_content TEXT,
                    processed_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    status TEXT DEFAULT 'processed',
                    error_message TEXT,
                    CONSTRAINT valid_command CHECK (command_type IN ('add_nudge', 'add_milestone', 'note', 'today', 'unknown'))
                )
            """)

            # Create indexes for common queries
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_nudges_status ON nudges(status)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_nudges_due ON nudges(due_datetime)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_sent_log_channel ON sent_log(channel)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_email_ingest_message_id ON email_ingest_log(message_id)")

    # =========================================================================
    # NUDGES
    # =========================================================================

    def add_nudge(
        self,
        content: str,
        due_datetime: Optional[str] = None,
        priority: str = "normal",
        source: str = "manual"
    ) -> int:
        """Add a new nudge/reminder."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO nudges (content, due_datetime, priority, source)
                VALUES (?, ?, ?, ?)
                """,
                (content, due_datetime, priority, source)
            )
            return cursor.lastrowid

    def get_pending_nudges(self, include_future: bool = True) -> List[Dict[str, Any]]:
        """Get all pending nudges."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            if include_future:
                cursor.execute(
                    "SELECT * FROM nudges WHERE status = 'pending' ORDER BY due_datetime"
                )
            else:
                now = datetime.now().isoformat()
                cursor.execute(
                    """
                    SELECT * FROM nudges
                    WHERE status = 'pending' AND (due_datetime IS NULL OR due_datetime <= ?)
                    ORDER BY due_datetime
                    """,
                    (now,)
                )
            return [dict(row) for row in cursor.fetchall()]

    def get_nudges_for_date(self, date: str) -> List[Dict[str, Any]]:
        """Get nudges due on a specific date (YYYY-MM-DD format)."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT * FROM nudges
                WHERE status = 'pending' AND due_datetime LIKE ?
                ORDER BY due_datetime
                """,
                (f"{date}%",)
            )
            return [dict(row) for row in cursor.fetchall()]

    def mark_nudge_sent(self, nudge_id: int):
        """Mark a nudge as sent."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE nudges SET status = 'sent' WHERE id = ?",
                (nudge_id,)
            )

    def complete_nudge(self, nudge_id: int):
        """Mark a nudge as completed."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE nudges SET status = 'completed', completed_at = ? WHERE id = ?",
                (datetime.now().isoformat(), nudge_id)
            )

    # =========================================================================
    # NOTES
    # =========================================================================

    def add_note(self, content: str, tags: str = None, source: str = "manual") -> int:
        """Add a new note."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO notes (content, tags, source) VALUES (?, ?, ?)",
                (content, tags, source)
            )
            return cursor.lastrowid

    def get_recent_notes(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent notes."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM notes ORDER BY created_at DESC LIMIT ?",
                (limit,)
            )
            return [dict(row) for row in cursor.fetchall()]

    def search_notes(self, query: str) -> List[Dict[str, Any]]:
        """Search notes by content or tags."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT * FROM notes
                WHERE content LIKE ? OR tags LIKE ?
                ORDER BY created_at DESC
                """,
                (f"%{query}%", f"%{query}%")
            )
            return [dict(row) for row in cursor.fetchall()]

    # =========================================================================
    # SENT LOG
    # =========================================================================

    def log_sent(
        self,
        channel: str,
        recipient: str,
        content: str,
        subject: str = None,
        status: str = "sent",
        error_message: str = None
    ) -> int:
        """Log a sent notification."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO sent_log (channel, recipient, subject, content, status, error_message)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (channel, recipient, subject, content, status, error_message)
            )
            return cursor.lastrowid

    def get_sent_log(self, channel: str = None, limit: int = 50) -> List[Dict[str, Any]]:
        """Get sent notification log."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            if channel:
                cursor.execute(
                    "SELECT * FROM sent_log WHERE channel = ? ORDER BY sent_at DESC LIMIT ?",
                    (channel, limit)
                )
            else:
                cursor.execute(
                    "SELECT * FROM sent_log ORDER BY sent_at DESC LIMIT ?",
                    (limit,)
                )
            return [dict(row) for row in cursor.fetchall()]

    # =========================================================================
    # EMAIL INGEST LOG
    # =========================================================================

    def log_email_ingest(
        self,
        message_id: str,
        subject: str,
        sender: str,
        command_type: str,
        command_content: str = None,
        status: str = "processed",
        error_message: str = None
    ) -> int:
        """Log a processed email trigger."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO email_ingest_log
                (message_id, subject, sender, command_type, command_content, status, error_message)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (message_id, subject, sender, command_type, command_content, status, error_message)
            )
            return cursor.lastrowid

    def is_email_processed(self, message_id: str) -> bool:
        """Check if an email has already been processed."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT 1 FROM email_ingest_log WHERE message_id = ?",
                (message_id,)
            )
            return cursor.fetchone() is not None

    def get_email_ingest_log(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get email ingest log."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM email_ingest_log ORDER BY processed_at DESC LIMIT ?",
                (limit,)
            )
            return [dict(row) for row in cursor.fetchall()]


def init_db(db_path: str = None) -> Database:
    """Initialize and return a Database instance."""
    return Database(db_path)
