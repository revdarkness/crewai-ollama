"""
Gmail IMAP Integration for Teaching Assistant Crew.

Reads emails from a specific Gmail label (TA-TRIGGERS) and parses commands.
"""

import os
import re
import email
import imaplib
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
from email.header import decode_header


class GmailIMAPClient:
    """Gmail IMAP client for reading trigger emails."""

    # Command patterns
    COMMAND_PATTERNS = {
        "add_nudge": re.compile(r"ADD\s+NUDGE:\s*(.+)", re.IGNORECASE),
        "add_milestone": re.compile(r"ADD\s+MILESTONE:\s*(.+)", re.IGNORECASE),
        "note": re.compile(r"NOTE:\s*(.+)", re.IGNORECASE),
        "today": re.compile(r"TODAY\??", re.IGNORECASE),
    }

    def __init__(
        self,
        host: str = None,
        user: str = None,
        password: str = None,
        label: str = None
    ):
        """
        Initialize Gmail IMAP client.

        Args:
            host: IMAP server host
            user: Gmail address
            password: Gmail app password
            label: Gmail label to monitor (default: TA-TRIGGERS)
        """
        self.host = host or os.getenv("IMAP_HOST", "imap.gmail.com")
        self.user = user or os.getenv("IMAP_USER")
        self.password = password or os.getenv("IMAP_PASS")
        self.label = label or os.getenv("IMAP_LABEL", "TA-TRIGGERS")
        self._connection = None

        if not self.user or not self.password:
            raise ValueError(
                "Gmail credentials required. Set IMAP_USER and IMAP_PASS environment variables."
            )

    def connect(self) -> bool:
        """
        Connect to Gmail IMAP server.

        Returns:
            True if connection successful
        """
        try:
            self._connection = imaplib.IMAP4_SSL(self.host)
            self._connection.login(self.user, self.password)
            return True
        except imaplib.IMAP4.error as e:
            raise ConnectionError(f"Failed to connect to Gmail: {e}")

    def disconnect(self):
        """Close IMAP connection."""
        if self._connection:
            try:
                self._connection.logout()
            except:
                pass
            self._connection = None

    def _ensure_connected(self):
        """Ensure IMAP connection is active."""
        if not self._connection:
            self.connect()

    def get_unread_triggers(self) -> List[Dict[str, Any]]:
        """
        Get unread emails from the trigger label.

        Returns:
            List of email dictionaries with parsed commands
        """
        self._ensure_connected()

        # Select the label/folder
        # Gmail labels are accessed as folders with the label name
        try:
            status, _ = self._connection.select(f'"{self.label}"')
            if status != "OK":
                # Try with INBOX and search by label
                self._connection.select("INBOX")
        except:
            self._connection.select("INBOX")

        # Search for unread messages
        status, messages = self._connection.search(None, "UNSEEN")
        if status != "OK":
            return []

        email_ids = messages[0].split()
        emails = []

        for email_id in email_ids:
            try:
                email_data = self._fetch_email(email_id)
                if email_data:
                    # Parse command from email
                    command = self._parse_command(email_data)
                    email_data["command"] = command
                    emails.append(email_data)
            except Exception as e:
                print(f"Error fetching email {email_id}: {e}")

        return emails

    def _fetch_email(self, email_id: bytes) -> Optional[Dict[str, Any]]:
        """
        Fetch and parse a single email.

        Args:
            email_id: IMAP email ID

        Returns:
            Parsed email dictionary
        """
        status, msg_data = self._connection.fetch(email_id, "(RFC822)")
        if status != "OK":
            return None

        for response_part in msg_data:
            if isinstance(response_part, tuple):
                msg = email.message_from_bytes(response_part[1])

                # Decode subject
                subject, encoding = decode_header(msg["Subject"])[0]
                if isinstance(subject, bytes):
                    subject = subject.decode(encoding or "utf-8")

                # Get sender
                sender = msg.get("From", "")

                # Get message ID
                message_id = msg.get("Message-ID", str(email_id))

                # Get body
                body = self._get_email_body(msg)

                return {
                    "message_id": message_id,
                    "subject": subject,
                    "sender": sender,
                    "body": body,
                    "date": msg.get("Date"),
                }

        return None

    def _get_email_body(self, msg) -> str:
        """Extract plain text body from email message."""
        body = ""

        if msg.is_multipart():
            for part in msg.walk():
                content_type = part.get_content_type()
                if content_type == "text/plain":
                    try:
                        payload = part.get_payload(decode=True)
                        if payload:
                            body = payload.decode("utf-8", errors="ignore")
                            break
                    except:
                        pass
        else:
            try:
                payload = msg.get_payload(decode=True)
                if payload:
                    body = payload.decode("utf-8", errors="ignore")
            except:
                body = msg.get_payload()

        return body.strip()

    def _parse_command(self, email_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Parse command from email subject and body.

        Args:
            email_data: Email dictionary with subject and body

        Returns:
            Command dictionary with type and content
        """
        # Check subject first, then body
        text_to_check = f"{email_data.get('subject', '')} {email_data.get('body', '')}"

        for cmd_type, pattern in self.COMMAND_PATTERNS.items():
            match = pattern.search(text_to_check)
            if match:
                content = match.group(1).strip() if match.lastindex else None
                return {
                    "type": cmd_type,
                    "content": content,
                    "raw_match": match.group(0)
                }

        return {
            "type": "unknown",
            "content": None,
            "raw_match": None
        }

    def mark_as_read(self, email_id: bytes):
        """Mark an email as read."""
        self._ensure_connected()
        self._connection.store(email_id, "+FLAGS", "\\Seen")

    def __enter__(self):
        """Context manager entry."""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.disconnect()


class MockGmailIMAPClient:
    """Mock client for testing without Gmail access."""

    def __init__(self, *args, **kwargs):
        self.label = kwargs.get("label", "TA-TRIGGERS")

    def connect(self) -> bool:
        return True

    def disconnect(self):
        pass

    def get_unread_triggers(self) -> List[Dict[str, Any]]:
        """Return mock trigger emails for testing."""
        return [
            {
                "message_id": "<mock1@example.com>",
                "subject": "[TA] ADD NUDGE: Print CO2 car rubrics tomorrow at 7:15am",
                "sender": "teacher@school.edu",
                "body": "",
                "date": datetime.now().isoformat(),
                "command": {
                    "type": "add_nudge",
                    "content": "Print CO2 car rubrics tomorrow at 7:15am",
                    "raw_match": "ADD NUDGE: Print CO2 car rubrics tomorrow at 7:15am"
                }
            },
        ]

    def mark_as_read(self, email_id: bytes):
        pass

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass


def parse_datetime_from_text(text: str) -> Optional[datetime]:
    """
    Parse natural language datetime from text.

    Supports patterns like:
    - "tomorrow at 7:15am"
    - "Feb 10 at 4pm"
    - "next Monday at 3:00pm"

    Args:
        text: Natural language datetime string

    Returns:
        Parsed datetime or None if parsing fails
    """
    try:
        from dateutil import parser as date_parser
        from dateutil.relativedelta import relativedelta

        # Handle relative terms
        text_lower = text.lower()
        now = datetime.now()

        if "tomorrow" in text_lower:
            base_date = now + relativedelta(days=1)
            # Extract time
            time_match = re.search(r"(\d{1,2}):?(\d{2})?\s*(am|pm)?", text_lower)
            if time_match:
                hour = int(time_match.group(1))
                minute = int(time_match.group(2) or 0)
                period = time_match.group(3)
                if period == "pm" and hour < 12:
                    hour += 12
                elif period == "am" and hour == 12:
                    hour = 0
                return base_date.replace(hour=hour, minute=minute, second=0, microsecond=0)
            return base_date.replace(hour=9, minute=0, second=0, microsecond=0)

        # Use dateutil for other formats
        return date_parser.parse(text, fuzzy=True)

    except ImportError:
        print("dateutil not installed. Run: pip install python-dateutil")
        return None
    except Exception:
        return None
