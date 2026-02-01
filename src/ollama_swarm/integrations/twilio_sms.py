"""
Twilio SMS Integration for Teaching Assistant Crew.

Sends SMS notifications and condensed briefings.
"""

import os
from typing import Optional, List
from datetime import datetime


try:
    from twilio.rest import Client as TwilioClient
    TWILIO_AVAILABLE = True
except ImportError:
    TWILIO_AVAILABLE = False


class TwilioSMSClient:
    """Twilio client for sending SMS notifications."""

    # SMS character limit for single message
    SMS_LIMIT = 160

    def __init__(
        self,
        account_sid: str = None,
        auth_token: str = None,
        from_number: str = None,
        to_number: str = None
    ):
        """
        Initialize Twilio SMS client.

        Args:
            account_sid: Twilio Account SID
            auth_token: Twilio Auth Token
            from_number: Twilio phone number to send from
            to_number: Default recipient phone number
        """
        if not TWILIO_AVAILABLE:
            raise ImportError(
                "Twilio library not installed. Run: pip install twilio"
            )

        self.account_sid = account_sid or os.getenv("TWILIO_ACCOUNT_SID")
        self.auth_token = auth_token or os.getenv("TWILIO_AUTH_TOKEN")
        self.from_number = from_number or os.getenv("TWILIO_FROM")
        self.to_number = to_number or os.getenv("TWILIO_TO")

        if not all([self.account_sid, self.auth_token, self.from_number]):
            raise ValueError(
                "Twilio credentials required. Set TWILIO_ACCOUNT_SID, "
                "TWILIO_AUTH_TOKEN, and TWILIO_FROM environment variables."
            )

        self.client = TwilioClient(self.account_sid, self.auth_token)

    def send_sms(self, message: str, to: str = None) -> dict:
        """
        Send an SMS message.

        Args:
            message: Message text
            to: Recipient phone number (default: TWILIO_TO)

        Returns:
            Dictionary with 'success', 'sid', and 'error' keys
        """
        to = to or self.to_number
        if not to:
            return {"success": False, "sid": None, "error": "No recipient specified"}

        try:
            msg = self.client.messages.create(
                body=message,
                from_=self.from_number,
                to=to
            )
            return {"success": True, "sid": msg.sid, "error": None}

        except Exception as e:
            return {"success": False, "sid": None, "error": str(e)}

    def send_daily_summary(
        self,
        schedule: List[dict],
        milestones: List[dict],
        nudges: List[dict],
        to: str = None
    ) -> dict:
        """
        Send a condensed daily summary via SMS.

        Args:
            schedule: Today's teaching schedule
            milestones: Upcoming milestones
            nudges: Active nudges/reminders
            to: Recipient phone number

        Returns:
            Send result dictionary
        """
        lines = []

        # Today's classes (abbreviated)
        if schedule:
            class_count = len(schedule)
            first_class = schedule[0].get("summary", "Class")[:20]
            lines.append(f"Today: {class_count} classes, starts {first_class}")

        # Urgent items
        urgent_nudges = [n for n in nudges if n.get("priority") in ["high", "urgent"]]
        if urgent_nudges:
            lines.append(f"URGENT: {urgent_nudges[0].get('content', '')[:40]}")

        # Upcoming milestones (next 3 days)
        if milestones:
            lines.append(f"Due soon: {milestones[0].get('summary', '')[:30]}")

        # Combine and truncate
        message = " | ".join(lines)
        if len(message) > self.SMS_LIMIT:
            message = message[:self.SMS_LIMIT - 3] + "..."

        return self.send_sms(message, to)

    def send_conflict_alert(
        self,
        event: str,
        conflict: str,
        to: str = None
    ) -> dict:
        """
        Send a calendar conflict alert via SMS.

        Args:
            event: Proposed event that couldn't be created
            conflict: Conflicting event
            to: Recipient phone number

        Returns:
            Send result dictionary
        """
        message = f"CONFLICT: '{event[:30]}' conflicts with '{conflict[:30]}'. Check email."
        if len(message) > self.SMS_LIMIT:
            message = message[:self.SMS_LIMIT - 3] + "..."

        return self.send_sms(message, to)

    def send_nudge_reminder(self, nudge: dict, to: str = None) -> dict:
        """
        Send a single nudge reminder via SMS.

        Args:
            nudge: Nudge dictionary
            to: Recipient phone number

        Returns:
            Send result dictionary
        """
        content = nudge.get("content", "Reminder")
        priority = nudge.get("priority", "normal")

        prefix = "URGENT: " if priority in ["high", "urgent"] else ""
        message = f"{prefix}{content}"

        if len(message) > self.SMS_LIMIT:
            message = message[:self.SMS_LIMIT - 3] + "..."

        return self.send_sms(message, to)


class MockTwilioSMSClient:
    """Mock Twilio client for testing without Twilio credentials."""

    SMS_LIMIT = 160

    def __init__(self, *args, **kwargs):
        self.sent_messages = []
        self.to_number = kwargs.get("to_number") or os.getenv("TWILIO_TO", "+1234567890")

    def send_sms(self, message: str, to: str = None) -> dict:
        to = to or self.to_number
        self.sent_messages.append({
            "message": message,
            "to": to,
            "timestamp": datetime.now().isoformat()
        })
        print(f"[MOCK SMS] To: {to}, Message: {message[:50]}...")
        return {"success": True, "sid": "MOCK_SID", "error": None}

    def send_daily_summary(self, schedule, milestones, nudges, to=None) -> dict:
        summary = f"Today: {len(schedule)} classes | {len(milestones)} milestones | {len(nudges)} reminders"
        return self.send_sms(summary, to)

    def send_conflict_alert(self, event: str, conflict: str, to: str = None) -> dict:
        return self.send_sms(f"CONFLICT: {event[:30]} vs {conflict[:30]}", to)

    def send_nudge_reminder(self, nudge: dict, to: str = None) -> dict:
        return self.send_sms(nudge.get("content", "Reminder")[:150], to)
