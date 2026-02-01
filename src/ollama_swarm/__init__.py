"""
Teaching Assistant Crew - AI-powered teaching assistant.

A CrewAI-based system that helps educators manage schedules, projects,
and communications using local Ollama models.

Components:
- Agents: Schedule Reader, Project Pulse, Nudge Composer
- Integrations: Google Calendar, Gmail IMAP, SMTP, Twilio SMS
- Database: SQLite for local audit trail
"""

from .database import Database, init_db
from .agents import TeachingAssistantCrew

__version__ = "0.1.0"
__all__ = [
    "Database",
    "init_db",
    "TeachingAssistantCrew",
]
