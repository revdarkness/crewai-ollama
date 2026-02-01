"""
Google Calendar Integration for Teaching Assistant Crew.

Provides read/write access to Google Calendar with conflict detection.
"""

import os
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import json

try:
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build
    GOOGLE_AVAILABLE = True
except ImportError:
    GOOGLE_AVAILABLE = False


# OAuth scopes for Calendar access
SCOPES = ["https://www.googleapis.com/auth/calendar"]


class GoogleCalendarClient:
    """Google Calendar API client with conflict detection."""

    def __init__(
        self,
        credentials_path: str = "credentials.json",
        token_path: str = "token.json"
    ):
        """
        Initialize Google Calendar client.

        Args:
            credentials_path: Path to OAuth credentials file
            token_path: Path to store/load token
        """
        if not GOOGLE_AVAILABLE:
            raise ImportError(
                "Google API libraries not installed. "
                "Run: pip install google-auth-oauthlib google-api-python-client"
            )

        self.credentials_path = credentials_path
        self.token_path = token_path
        self.service = None
        self._schedule_calendar_id = os.getenv("GCAL_CALENDAR_ID_SCHEDULE", "primary")
        self._projects_calendar_id = os.getenv("GCAL_CALENDAR_ID_PROJECTS", "primary")

    def authenticate(self) -> bool:
        """
        Authenticate with Google Calendar API.

        Returns:
            True if authentication successful
        """
        creds = None

        # Load existing token
        if os.path.exists(self.token_path):
            creds = Credentials.from_authorized_user_file(self.token_path, SCOPES)

        # Refresh or get new credentials
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                if not os.path.exists(self.credentials_path):
                    raise FileNotFoundError(
                        f"Credentials file not found: {self.credentials_path}\n"
                        "Download from Google Cloud Console."
                    )
                flow = InstalledAppFlow.from_client_secrets_file(
                    self.credentials_path, SCOPES
                )
                creds = flow.run_local_server(port=0)

            # Save credentials for next run
            with open(self.token_path, "w") as token:
                token.write(creds.to_json())

        self.service = build("calendar", "v3", credentials=creds)
        return True

    def _ensure_authenticated(self):
        """Ensure client is authenticated."""
        if not self.service:
            self.authenticate()

    # =========================================================================
    # READ OPERATIONS
    # =========================================================================

    def get_today_events(self, calendar_id: str = None) -> List[Dict[str, Any]]:
        """
        Get all events for today.

        Args:
            calendar_id: Calendar to read from (default: schedule calendar)

        Returns:
            List of event dictionaries
        """
        self._ensure_authenticated()
        calendar_id = calendar_id or self._schedule_calendar_id

        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        tomorrow = today + timedelta(days=1)

        events_result = self.service.events().list(
            calendarId=calendar_id,
            timeMin=today.isoformat() + "Z",
            timeMax=tomorrow.isoformat() + "Z",
            singleEvents=True,
            orderBy="startTime"
        ).execute()

        return self._parse_events(events_result.get("items", []))

    def get_upcoming_events(
        self,
        days: int = 7,
        calendar_id: str = None
    ) -> List[Dict[str, Any]]:
        """
        Get events for the next N days.

        Args:
            days: Number of days to look ahead
            calendar_id: Calendar to read from (default: projects calendar)

        Returns:
            List of event dictionaries
        """
        self._ensure_authenticated()
        calendar_id = calendar_id or self._projects_calendar_id

        now = datetime.now()
        future = now + timedelta(days=days)

        events_result = self.service.events().list(
            calendarId=calendar_id,
            timeMin=now.isoformat() + "Z",
            timeMax=future.isoformat() + "Z",
            singleEvents=True,
            orderBy="startTime"
        ).execute()

        return self._parse_events(events_result.get("items", []))

    def get_milestones(self, days: int = 14) -> List[Dict[str, Any]]:
        """
        Get project milestones for the next N days.

        Args:
            days: Number of days to look ahead (default: 14)

        Returns:
            List of milestone events
        """
        return self.get_upcoming_events(days, self._projects_calendar_id)

    def get_teaching_schedule(self) -> List[Dict[str, Any]]:
        """Get today's teaching schedule."""
        return self.get_today_events(self._schedule_calendar_id)

    # =========================================================================
    # WRITE OPERATIONS
    # =========================================================================

    def check_conflict(
        self,
        start_time: datetime,
        end_time: datetime,
        calendar_id: str = None
    ) -> List[Dict[str, Any]]:
        """
        Check for calendar conflicts in a time range.

        Args:
            start_time: Start of proposed event
            end_time: End of proposed event
            calendar_id: Calendar to check

        Returns:
            List of conflicting events (empty if no conflicts)
        """
        self._ensure_authenticated()
        calendar_id = calendar_id or self._projects_calendar_id

        events_result = self.service.events().list(
            calendarId=calendar_id,
            timeMin=start_time.isoformat() + "Z",
            timeMax=end_time.isoformat() + "Z",
            singleEvents=True,
            orderBy="startTime"
        ).execute()

        return self._parse_events(events_result.get("items", []))

    def create_event(
        self,
        summary: str,
        start_time: datetime,
        end_time: datetime = None,
        description: str = None,
        calendar_id: str = None,
        check_conflicts: bool = True
    ) -> Dict[str, Any]:
        """
        Create a calendar event with optional conflict detection.

        Args:
            summary: Event title
            start_time: Event start time
            end_time: Event end time (default: 1 hour after start)
            description: Event description
            calendar_id: Calendar to add event to
            check_conflicts: Whether to check for conflicts first

        Returns:
            Dictionary with 'success', 'event' or 'conflicts' keys
        """
        self._ensure_authenticated()
        calendar_id = calendar_id or self._projects_calendar_id

        if end_time is None:
            end_time = start_time + timedelta(hours=1)

        # Check for conflicts if requested
        if check_conflicts:
            conflicts = self.check_conflict(start_time, end_time, calendar_id)
            if conflicts:
                return {
                    "success": False,
                    "reason": "conflict",
                    "conflicts": conflicts
                }

        # Create the event
        event = {
            "summary": summary,
            "start": {
                "dateTime": start_time.isoformat(),
                "timeZone": os.getenv("TIMEZONE", "America/Chicago"),
            },
            "end": {
                "dateTime": end_time.isoformat(),
                "timeZone": os.getenv("TIMEZONE", "America/Chicago"),
            },
        }

        if description:
            event["description"] = description

        created_event = self.service.events().insert(
            calendarId=calendar_id,
            body=event
        ).execute()

        return {
            "success": True,
            "event": self._parse_event(created_event)
        }

    def create_milestone(
        self,
        title: str,
        due_datetime: datetime,
        description: str = None
    ) -> Dict[str, Any]:
        """
        Create a project milestone event.

        Args:
            title: Milestone title
            due_datetime: When the milestone is due
            description: Additional details

        Returns:
            Result dictionary with success status
        """
        return self.create_event(
            summary=f"[MILESTONE] {title}",
            start_time=due_datetime,
            end_time=due_datetime + timedelta(hours=1),
            description=description,
            calendar_id=self._projects_calendar_id,
            check_conflicts=True
        )

    # =========================================================================
    # HELPERS
    # =========================================================================

    def _parse_events(self, events: List[Dict]) -> List[Dict[str, Any]]:
        """Parse a list of Google Calendar events."""
        return [self._parse_event(e) for e in events]

    def _parse_event(self, event: Dict) -> Dict[str, Any]:
        """Parse a single Google Calendar event into a simpler format."""
        start = event.get("start", {})
        end = event.get("end", {})

        return {
            "id": event.get("id"),
            "summary": event.get("summary", "Untitled"),
            "description": event.get("description"),
            "start": start.get("dateTime") or start.get("date"),
            "end": end.get("dateTime") or end.get("date"),
            "location": event.get("location"),
            "link": event.get("htmlLink"),
            "all_day": "date" in start,
        }


class MockGoogleCalendarClient:
    """Mock client for testing without Google API access."""

    def __init__(self, *args, **kwargs):
        pass

    def authenticate(self) -> bool:
        return True

    def get_today_events(self, calendar_id: str = None) -> List[Dict[str, Any]]:
        return [
            {
                "id": "mock1",
                "summary": "Period 1 - Engineering Design",
                "start": "2025-01-31T08:00:00",
                "end": "2025-01-31T09:30:00",
                "all_day": False,
            },
            {
                "id": "mock2",
                "summary": "Period 3 - Robotics",
                "start": "2025-01-31T10:30:00",
                "end": "2025-01-31T12:00:00",
                "all_day": False,
            },
        ]

    def get_upcoming_events(self, days: int = 7, calendar_id: str = None) -> List[Dict[str, Any]]:
        return [
            {
                "id": "mock3",
                "summary": "[MILESTONE] CDR Slides Due",
                "start": "2025-02-05T16:00:00",
                "end": "2025-02-05T17:00:00",
                "all_day": False,
            },
        ]

    def get_milestones(self, days: int = 14) -> List[Dict[str, Any]]:
        return self.get_upcoming_events(days)

    def get_teaching_schedule(self) -> List[Dict[str, Any]]:
        return self.get_today_events()

    def check_conflict(self, start_time, end_time, calendar_id=None) -> List[Dict]:
        return []

    def create_event(self, summary, start_time, **kwargs) -> Dict[str, Any]:
        return {"success": True, "event": {"id": "new_mock", "summary": summary}}

    def create_milestone(self, title, due_datetime, description=None) -> Dict[str, Any]:
        return {"success": True, "event": {"id": "new_milestone", "summary": title}}
