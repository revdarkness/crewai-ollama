#!/usr/bin/env python3
"""
Teaching Assistant Crew - Main Entry Point

Run the Teaching Assistant AI Crew powered by Ollama models.

Operating Modes:
    teacher_daily - Generate daily briefing (6 AM scheduled)
    email_ingest  - Process trigger emails (every 10-15 min)

Usage:
    python -m ollama_swarm.main "daily briefing" --mode teacher_daily
    python -m ollama_swarm.main "email ingest" --mode email_ingest
    python -m ollama_swarm.main --test  # Run with mock data
"""

import argparse
import os
import sys
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


def run_daily_briefing(model: str = None, use_mock: bool = False):
    """
    Run the daily briefing mode.

    Generates and sends a daily briefing via email and SMS.
    """
    print("\n" + "=" * 60)
    print("  TEACHING ASSISTANT - Daily Briefing Mode")
    print("=" * 60)
    print(f"  Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  Model: {model or os.getenv('OLLAMA_MODEL', 'llama3:latest')}")
    print(f"  Mock Mode: {use_mock}")
    print("=" * 60 + "\n")

    # Import components
    from .database import Database
    from .agents import TeachingAssistantCrew

    if use_mock:
        from .integrations.google_calendar import MockGoogleCalendarClient as CalendarClient
        from .integrations.smtp_sender import MockSMTPSender as SMTPSender
        from .integrations.twilio_sms import MockTwilioSMSClient as SMSClient
    else:
        from .integrations.google_calendar import GoogleCalendarClient as CalendarClient
        from .integrations.smtp_sender import SMTPSender
        from .integrations.twilio_sms import TwilioSMSClient as SMSClient

    # Initialize components
    db = Database()
    calendar = CalendarClient()
    smtp = SMTPSender() if not use_mock else MockSMTPSender()

    try:
        sms = SMSClient() if not use_mock else MockTwilioSMSClient()
    except (ImportError, ValueError) as e:
        print(f"SMS disabled: {e}")
        sms = None

    # Authenticate calendar if not mock
    if not use_mock:
        print("Authenticating with Google Calendar...")
        calendar.authenticate()

    # Gather data
    print("Gathering schedule and milestones...")
    schedule = calendar.get_teaching_schedule()
    milestones = calendar.get_milestones(days=14)
    nudges = db.get_pending_nudges()
    notes = db.get_recent_notes(limit=10)

    print(f"  - {len(schedule)} events today")
    print(f"  - {len(milestones)} milestones (14 days)")
    print(f"  - {len(nudges)} active nudges")
    print(f"  - {len(notes)} recent notes")

    # Run the crew
    print("\nRunning Teaching Assistant Crew...")
    crew = TeachingAssistantCrew(model=model)
    result = crew.run_daily_briefing(
        schedule_events=schedule,
        milestones=milestones,
        nudges=nudges,
        notes=notes
    )

    # Send notifications
    print("\nSending notifications...")

    # Email briefing
    email_result = smtp.send_daily_briefing(
        schedule=schedule,
        milestones=milestones,
        nudges=nudges,
        notes=notes
    )
    if email_result["success"]:
        print("  - Email briefing sent")
        db.log_sent("email", os.getenv("NOTIFY_EMAIL_TO", ""), result["email_briefing"][:500])
    else:
        print(f"  - Email failed: {email_result['error']}")

    # SMS summary
    if sms:
        sms_result = sms.send_daily_summary(
            schedule=schedule,
            milestones=milestones,
            nudges=nudges
        )
        if sms_result["success"]:
            print("  - SMS summary sent")
            db.log_sent("sms", os.getenv("TWILIO_TO", ""), result["sms_summary"])
        else:
            print(f"  - SMS failed: {sms_result['error']}")

    print("\n" + "=" * 60)
    print("  Daily Briefing Complete")
    print("=" * 60)

    return result


def run_email_ingest(model: str = None, use_mock: bool = False):
    """
    Run the email ingest mode.

    Polls Gmail for trigger emails and processes commands.
    """
    print("\n" + "=" * 60)
    print("  TEACHING ASSISTANT - Email Ingest Mode")
    print("=" * 60)
    print(f"  Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  Mock Mode: {use_mock}")
    print("=" * 60 + "\n")

    # Import components
    from .database import Database
    from .agents import TeachingAssistantCrew
    from .integrations.gmail_imap import parse_datetime_from_text

    if use_mock:
        from .integrations.gmail_imap import MockGmailIMAPClient as IMAPClient
        from .integrations.google_calendar import MockGoogleCalendarClient as CalendarClient
        from .integrations.smtp_sender import MockSMTPSender as SMTPSender
        from .integrations.twilio_sms import MockTwilioSMSClient as SMSClient
    else:
        from .integrations.gmail_imap import GmailIMAPClient as IMAPClient
        from .integrations.google_calendar import GoogleCalendarClient as CalendarClient
        from .integrations.smtp_sender import SMTPSender
        from .integrations.twilio_sms import TwilioSMSClient as SMSClient

    # Initialize components
    db = Database()
    crew = TeachingAssistantCrew(model=model)

    try:
        calendar = CalendarClient()
        if not use_mock:
            calendar.authenticate()
    except Exception as e:
        print(f"Calendar unavailable: {e}")
        calendar = None

    try:
        smtp = SMTPSender() if not use_mock else MockSMTPSender()
    except ValueError:
        smtp = None

    try:
        sms = SMSClient() if not use_mock else MockTwilioSMSClient()
    except (ImportError, ValueError):
        sms = None

    # Connect to Gmail
    print("Connecting to Gmail...")
    with IMAPClient() if not use_mock else MockGmailIMAPClient() as imap:
        # Get unread trigger emails
        emails = imap.get_unread_triggers()
        print(f"Found {len(emails)} unread trigger emails\n")

        for email_data in emails:
            message_id = email_data.get("message_id", "unknown")
            subject = email_data.get("subject", "")
            command = email_data.get("command", {})
            cmd_type = command.get("type", "unknown")
            cmd_content = command.get("content", "")

            print(f"Processing: {subject[:50]}...")
            print(f"  Command: {cmd_type}")

            # Skip if already processed
            if db.is_email_processed(message_id):
                print("  Already processed, skipping.")
                continue

            # Process command
            try:
                if cmd_type == "add_nudge":
                    # Parse datetime from content
                    due_dt = parse_datetime_from_text(cmd_content)
                    due_str = due_dt.isoformat() if due_dt else None

                    nudge_id = db.add_nudge(
                        content=cmd_content,
                        due_datetime=due_str,
                        source="email"
                    )
                    print(f"  Added nudge #{nudge_id}")

                elif cmd_type == "add_milestone":
                    # Parse milestone details
                    due_dt = parse_datetime_from_text(cmd_content)

                    if calendar and due_dt:
                        result = calendar.create_milestone(
                            title=cmd_content,
                            due_datetime=due_dt
                        )

                        if result["success"]:
                            print(f"  Created milestone: {cmd_content[:30]}")
                        else:
                            # Conflict detected
                            conflicts = result.get("conflicts", [])
                            print(f"  CONFLICT detected with {len(conflicts)} event(s)")

                            # Notify teacher
                            if smtp:
                                smtp.send_conflict_notification(
                                    proposed_event=cmd_content,
                                    conflicts=conflicts
                                )
                            if sms and conflicts:
                                sms.send_conflict_alert(
                                    event=cmd_content,
                                    conflict=conflicts[0].get("summary", "existing event")
                                )
                    else:
                        print("  Could not parse date or calendar unavailable")

                elif cmd_type == "note":
                    note_id = db.add_note(content=cmd_content, source="email")
                    print(f"  Added note #{note_id}")

                elif cmd_type == "today":
                    # Quick check - run crew for response
                    if calendar:
                        schedule = calendar.get_teaching_schedule()
                    else:
                        schedule = []
                    nudges = db.get_pending_nudges()

                    response = crew.run_quick_check(schedule, nudges)
                    print(f"  Generated response")

                    # Send response via email
                    if smtp:
                        smtp.send_email(
                            subject="[TA] Today's Status",
                            body=response,
                            to=email_data.get("sender")
                        )

                else:
                    print(f"  Unknown command type: {cmd_type}")

                # Log the processed email
                db.log_email_ingest(
                    message_id=message_id,
                    subject=subject,
                    sender=email_data.get("sender", ""),
                    command_type=cmd_type,
                    command_content=cmd_content,
                    status="processed"
                )

            except Exception as e:
                print(f"  ERROR: {e}")
                db.log_email_ingest(
                    message_id=message_id,
                    subject=subject,
                    sender=email_data.get("sender", ""),
                    command_type=cmd_type,
                    command_content=cmd_content,
                    status="error",
                    error_message=str(e)
                )

    print("\n" + "=" * 60)
    print("  Email Ingest Complete")
    print("=" * 60)


def run():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Teaching Assistant Crew - AI-powered teaching assistant",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Operating Modes:
  teacher_daily  Generate and send daily briefing
  email_ingest   Process trigger emails from Gmail

Examples:
  %(prog)s --mode teacher_daily
  %(prog)s --mode email_ingest
  %(prog)s --mode teacher_daily --test
  %(prog)s --mode teacher_daily --model llama3:latest
        """,
    )

    parser.add_argument(
        "topic",
        nargs="?",
        default="daily briefing",
        help="Task description (optional)",
    )

    parser.add_argument(
        "--mode", "-M",
        choices=["teacher_daily", "email_ingest"],
        default="teacher_daily",
        help="Operating mode (default: teacher_daily)",
    )

    parser.add_argument(
        "--model", "-m",
        default=None,
        help="Ollama model to use (default: from .env or llama3:latest)",
    )

    parser.add_argument(
        "--test", "-t",
        action="store_true",
        help="Run in test mode with mock data (no real API calls)",
    )

    parser.add_argument(
        "--init-db",
        action="store_true",
        help="Initialize database and exit",
    )

    args = parser.parse_args()

    # Set dummy API key for Ollama
    os.environ["OPENAI_API_KEY"] = os.getenv("OPENAI_API_KEY", "ollama")

    # Handle --init-db
    if args.init_db:
        from .database import Database
        db = Database()
        print(f"Database initialized: {db.db_path}")
        return

    # Run selected mode
    try:
        if args.mode == "teacher_daily":
            run_daily_briefing(model=args.model, use_mock=args.test)
        elif args.mode == "email_ingest":
            run_email_ingest(model=args.model, use_mock=args.test)
    except KeyboardInterrupt:
        print("\n\nOperation cancelled by user.")
        sys.exit(0)
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


# Mock classes for when imports fail
class MockSMTPSender:
    def send_email(self, *args, **kwargs):
        print("[MOCK] Email would be sent")
        return {"success": True}
    def send_daily_briefing(self, *args, **kwargs):
        return self.send_email()
    def send_conflict_notification(self, *args, **kwargs):
        return self.send_email()

class MockTwilioSMSClient:
    def send_sms(self, *args, **kwargs):
        print("[MOCK] SMS would be sent")
        return {"success": True}
    def send_daily_summary(self, *args, **kwargs):
        return self.send_sms()
    def send_conflict_alert(self, *args, **kwargs):
        return self.send_sms()

class MockGmailIMAPClient:
    def __enter__(self):
        return self
    def __exit__(self, *args):
        pass
    def get_unread_triggers(self):
        return []


if __name__ == "__main__":
    run()
