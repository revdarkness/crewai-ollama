"""
SMTP Email Sender for Teaching Assistant Crew.

Sends email notifications and daily briefings via Gmail SMTP.
"""

import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional, List
from datetime import datetime


class SMTPSender:
    """SMTP client for sending email notifications."""

    def __init__(
        self,
        host: str = None,
        port: int = None,
        user: str = None,
        password: str = None
    ):
        """
        Initialize SMTP sender.

        Args:
            host: SMTP server host
            port: SMTP server port
            user: Gmail address
            password: Gmail app password
        """
        self.host = host or os.getenv("SMTP_HOST", "smtp.gmail.com")
        self.port = port or int(os.getenv("SMTP_PORT", "587"))
        self.user = user or os.getenv("SMTP_USER")
        self.password = password or os.getenv("SMTP_PASS")
        self.default_recipient = os.getenv("NOTIFY_EMAIL_TO")

        if not self.user or not self.password:
            raise ValueError(
                "SMTP credentials required. Set SMTP_USER and SMTP_PASS environment variables."
            )

    def send_email(
        self,
        subject: str,
        body: str,
        to: str = None,
        html: bool = False
    ) -> dict:
        """
        Send an email.

        Args:
            subject: Email subject
            body: Email body (plain text or HTML)
            to: Recipient email (default: NOTIFY_EMAIL_TO)
            html: Whether body is HTML

        Returns:
            Dictionary with 'success' and 'error' keys
        """
        to = to or self.default_recipient
        if not to:
            return {"success": False, "error": "No recipient specified"}

        try:
            # Create message
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = self.user
            msg["To"] = to

            # Attach body
            content_type = "html" if html else "plain"
            msg.attach(MIMEText(body, content_type))

            # Send
            with smtplib.SMTP(self.host, self.port) as server:
                server.starttls()
                server.login(self.user, self.password)
                server.sendmail(self.user, to, msg.as_string())

            return {"success": True, "error": None}

        except smtplib.SMTPAuthenticationError:
            return {
                "success": False,
                "error": "SMTP authentication failed. Check your app password."
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def send_daily_briefing(
        self,
        schedule: List[dict],
        milestones: List[dict],
        nudges: List[dict],
        notes: List[dict] = None,
        to: str = None
    ) -> dict:
        """
        Send a formatted daily briefing email.

        Args:
            schedule: Today's teaching schedule
            milestones: Upcoming milestones
            nudges: Active nudges/reminders
            notes: Recent notes (optional)
            to: Recipient email

        Returns:
            Send result dictionary
        """
        today = datetime.now().strftime("%A, %B %d, %Y")

        # Build HTML email
        html = f"""
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; }}
                h1 {{ color: #2c3e50; border-bottom: 2px solid #3498db; padding-bottom: 10px; }}
                h2 {{ color: #34495e; margin-top: 20px; }}
                .event {{ background: #f8f9fa; padding: 10px; margin: 5px 0; border-left: 3px solid #3498db; }}
                .milestone {{ background: #fff3cd; padding: 10px; margin: 5px 0; border-left: 3px solid #ffc107; }}
                .nudge {{ background: #d4edda; padding: 10px; margin: 5px 0; border-left: 3px solid #28a745; }}
                .note {{ background: #e2e3e5; padding: 10px; margin: 5px 0; border-left: 3px solid #6c757d; }}
                .time {{ color: #666; font-size: 0.9em; }}
                .priority-high {{ border-left-color: #dc3545 !important; }}
                .priority-urgent {{ border-left-color: #dc3545 !important; background: #f8d7da !important; }}
            </style>
        </head>
        <body>
            <h1>Daily Briefing</h1>
            <p><strong>{today}</strong></p>
        """

        # Today's Schedule
        html += "<h2>Today's Schedule</h2>"
        if schedule:
            for event in schedule:
                start = event.get("start", "")
                if "T" in str(start):
                    start = start.split("T")[1][:5]
                html += f"""
                <div class="event">
                    <strong>{event.get('summary', 'Event')}</strong>
                    <span class="time"> - {start}</span>
                </div>
                """
        else:
            html += "<p>No scheduled events today.</p>"

        # Upcoming Milestones
        html += "<h2>Upcoming Milestones</h2>"
        if milestones:
            for milestone in milestones:
                start = milestone.get("start", "")
                if "T" in str(start):
                    date_str = start.split("T")[0]
                else:
                    date_str = start
                html += f"""
                <div class="milestone">
                    <strong>{milestone.get('summary', 'Milestone')}</strong>
                    <span class="time"> - Due: {date_str}</span>
                </div>
                """
        else:
            html += "<p>No upcoming milestones.</p>"

        # Nudges/Reminders
        html += "<h2>Reminders</h2>"
        if nudges:
            for nudge in nudges:
                priority = nudge.get("priority", "normal")
                priority_class = f"priority-{priority}" if priority in ["high", "urgent"] else ""
                due = nudge.get("due_datetime", "")
                if due:
                    due = f" - Due: {due}"
                html += f"""
                <div class="nudge {priority_class}">
                    {nudge.get('content', '')}
                    <span class="time">{due}</span>
                </div>
                """
        else:
            html += "<p>No active reminders.</p>"

        # Recent Notes (if provided)
        if notes:
            html += "<h2>Recent Notes</h2>"
            for note in notes[:5]:  # Limit to 5 recent notes
                html += f"""
                <div class="note">
                    {note.get('content', '')}
                </div>
                """

        html += """
            <hr>
            <p style="color: #888; font-size: 0.8em;">
                Generated by Teaching Assistant Crew
            </p>
        </body>
        </html>
        """

        # Also create plain text version
        plain = f"DAILY BRIEFING - {today}\n\n"
        plain += "TODAY'S SCHEDULE:\n"
        for event in schedule:
            plain += f"  - {event.get('summary')}\n"
        plain += "\nUPCOMING MILESTONES:\n"
        for milestone in milestones:
            plain += f"  - {milestone.get('summary')}\n"
        plain += "\nREMINDERS:\n"
        for nudge in nudges:
            plain += f"  - {nudge.get('content')}\n"

        return self.send_email(
            subject=f"Teaching Assistant Daily Briefing - {today}",
            body=html,
            to=to,
            html=True
        )

    def send_conflict_notification(
        self,
        proposed_event: str,
        conflicts: List[dict],
        to: str = None
    ) -> dict:
        """
        Send a calendar conflict notification.

        Args:
            proposed_event: The event that couldn't be created
            conflicts: List of conflicting events
            to: Recipient email

        Returns:
            Send result dictionary
        """
        conflict_list = "\n".join(
            f"  - {c.get('summary')} ({c.get('start')})"
            for c in conflicts
        )

        body = f"""
Calendar Conflict Detected

The following event could NOT be added:
  {proposed_event}

It conflicts with:
{conflict_list}

Please resolve the conflict manually.

---
Teaching Assistant Crew
        """

        return self.send_email(
            subject="[TA] Calendar Conflict Detected",
            body=body,
            to=to,
            html=False
        )


class MockSMTPSender:
    """Mock SMTP sender for testing."""

    def __init__(self, *args, **kwargs):
        self.sent_emails = []

    def send_email(self, subject: str, body: str, to: str = None, html: bool = False) -> dict:
        self.sent_emails.append({
            "subject": subject,
            "body": body,
            "to": to,
            "html": html,
            "timestamp": datetime.now().isoformat()
        })
        print(f"[MOCK EMAIL] To: {to}, Subject: {subject}")
        return {"success": True, "error": None}

    def send_daily_briefing(self, schedule, milestones, nudges, notes=None, to=None) -> dict:
        return self.send_email(
            subject="[MOCK] Daily Briefing",
            body="Mock daily briefing content",
            to=to
        )

    def send_conflict_notification(self, proposed_event, conflicts, to=None) -> dict:
        return self.send_email(
            subject="[MOCK] Calendar Conflict",
            body=f"Mock conflict for: {proposed_event}",
            to=to
        )
