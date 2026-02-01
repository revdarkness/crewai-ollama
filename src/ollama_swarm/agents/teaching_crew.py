"""
Teaching Assistant Crew - Main Crew Definition.

Orchestrates the Schedule Reader, Project Pulse, and Nudge Composer agents.
"""

import os
from datetime import datetime
from typing import Optional, Dict, Any, List

from crewai import Crew, Task, Process, LLM

from .schedule_reader import create_schedule_reader_agent, SCHEDULE_ANALYSIS_TASK
from .project_pulse import create_project_pulse_agent, MILESTONE_ANALYSIS_TASK
from .nudge_composer import create_nudge_composer_agent, DAILY_BRIEFING_TASK


def get_ollama_llm(model: str = None) -> LLM:
    """Create an Ollama LLM instance."""
    model_name = model or os.getenv("OLLAMA_MODEL", "llama3:latest")
    ollama_host = os.getenv("OLLAMA_HOST", "http://localhost:11434")

    return LLM(
        model=f"ollama/{model_name}",
        base_url=ollama_host,
        temperature=0.4,
    )


class TeachingAssistantCrew:
    """
    Teaching Assistant Crew for daily briefings and task management.

    This crew coordinates three agents:
    1. Schedule Reader - Analyzes today's calendar
    2. Project Pulse - Tracks milestones and risks
    3. Nudge Composer - Creates briefings and responses
    """

    def __init__(self, model: str = None):
        """
        Initialize the Teaching Assistant Crew.

        Args:
            model: Ollama model to use (default: from env or llama3:latest)
        """
        self.llm = get_ollama_llm(model)

        # Create agents
        self.schedule_reader = create_schedule_reader_agent(self.llm)
        self.project_pulse = create_project_pulse_agent(self.llm)
        self.nudge_composer = create_nudge_composer_agent(self.llm)

    def run_daily_briefing(
        self,
        schedule_events: List[Dict],
        milestones: List[Dict],
        nudges: List[Dict],
        notes: List[Dict] = None
    ) -> Dict[str, Any]:
        """
        Run the full daily briefing workflow.

        Args:
            schedule_events: Today's calendar events
            milestones: Upcoming project milestones
            nudges: Active nudges/reminders
            notes: Recent notes (optional)

        Returns:
            Dictionary with 'email_briefing' and 'sms_summary' keys
        """
        notes = notes or []
        today = datetime.now().strftime("%A, %B %d, %Y")

        # Format data for tasks
        events_text = self._format_events(schedule_events)
        milestones_text = self._format_events(milestones)
        nudges_text = self._format_nudges(nudges)
        notes_text = self._format_notes(notes)

        # Task 1: Schedule Analysis
        schedule_task = Task(
            description=SCHEDULE_ANALYSIS_TASK.format(events=events_text),
            expected_output="A structured analysis of today's teaching schedule with prep windows identified",
            agent=self.schedule_reader,
        )

        # Task 2: Project/Milestone Analysis
        project_task = Task(
            description=MILESTONE_ANALYSIS_TASK.format(
                milestones=milestones_text,
                nudges=nudges_text,
                notes=notes_text
            ),
            expected_output="A prioritized analysis of upcoming milestones with risk flags",
            agent=self.project_pulse,
        )

        # Task 3: Compose Briefing (depends on previous tasks)
        # The context parameter passes outputs from schedule_task and project_task
        # to the Nudge Composer agent automatically
        briefing_task = Task(
            description=DAILY_BRIEFING_TASK.format(
                date=today,
                nudges=nudges_text
            ),
            expected_output="Two outputs: a formatted email briefing and an SMS summary under 160 characters",
            agent=self.nudge_composer,
            context=[schedule_task, project_task],
        )

        # Create and run crew
        crew = Crew(
            agents=[self.schedule_reader, self.project_pulse, self.nudge_composer],
            tasks=[schedule_task, project_task, briefing_task],
            process=Process.sequential,
            verbose=True,
        )

        result = crew.kickoff()

        # Parse the result to extract email and SMS portions
        return self._parse_briefing_result(str(result))

    def run_quick_check(
        self,
        schedule_events: List[Dict],
        nudges: List[Dict]
    ) -> str:
        """
        Run a quick status check (for TODAY? command).

        Args:
            schedule_events: Today's calendar events
            nudges: Active nudges

        Returns:
            Quick status response string
        """
        events_text = self._format_events(schedule_events)
        nudges_text = self._format_nudges(nudges)
        current_time = datetime.now().strftime("%I:%M %p")

        task = Task(
            description=f"""
            Provide a quick status check for a teacher asking "TODAY?"

            Current Time: {current_time}

            Today's Schedule:
            {events_text}

            Active Reminders:
            {nudges_text}

            Give a brief, friendly response covering:
            - What's next on the schedule
            - Any urgent reminders
            - A quick summary of the day

            Keep it concise - this should be readable in 30 seconds.
            """,
            expected_output="A brief, friendly status update",
            agent=self.nudge_composer,
        )

        crew = Crew(
            agents=[self.nudge_composer],
            tasks=[task],
            verbose=False,
        )

        return str(crew.kickoff())

    def process_command(
        self,
        command_type: str,
        command_content: str,
        context: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Process an email command using the appropriate agent.

        Args:
            command_type: Type of command (add_nudge, add_milestone, note, today)
            command_content: The command content
            context: Additional context (schedule, nudges, etc.)

        Returns:
            Processing result dictionary
        """
        context = context or {}

        if command_type == "today":
            response = self.run_quick_check(
                context.get("schedule", []),
                context.get("nudges", [])
            )
            return {"type": "response", "content": response}

        elif command_type == "add_nudge":
            # Parse and validate the nudge
            return {
                "type": "nudge",
                "content": command_content,
                "action": "add_to_database"
            }

        elif command_type == "add_milestone":
            # Parse and validate the milestone
            return {
                "type": "milestone",
                "content": command_content,
                "action": "add_to_calendar"
            }

        elif command_type == "note":
            return {
                "type": "note",
                "content": command_content,
                "action": "add_to_database"
            }

        return {"type": "unknown", "content": command_content}

    # =========================================================================
    # FORMATTING HELPERS
    # =========================================================================

    def _format_events(self, events: List[Dict]) -> str:
        """Format calendar events as readable text."""
        if not events:
            return "No events scheduled."

        lines = []
        for event in events:
            start = event.get("start", "")
            if "T" in str(start):
                time_str = start.split("T")[1][:5]
            else:
                time_str = start

            summary = event.get("summary", "Untitled Event")
            lines.append(f"- {time_str}: {summary}")

        return "\n".join(lines)

    def _format_nudges(self, nudges: List[Dict]) -> str:
        """Format nudges as readable text."""
        if not nudges:
            return "No active reminders."

        lines = []
        for nudge in nudges:
            priority = nudge.get("priority", "normal")
            prefix = "[URGENT] " if priority in ["high", "urgent"] else ""
            content = nudge.get("content", "")
            due = nudge.get("due_datetime", "")
            if due:
                due = f" (Due: {due})"
            lines.append(f"- {prefix}{content}{due}")

        return "\n".join(lines)

    def _format_notes(self, notes: List[Dict]) -> str:
        """Format notes as readable text."""
        if not notes:
            return "No recent notes."

        lines = []
        for note in notes[:10]:  # Limit to recent 10
            content = note.get("content", "")
            created = note.get("created_at", "")[:10] if note.get("created_at") else ""
            lines.append(f"- [{created}] {content}")

        return "\n".join(lines)

    def _parse_briefing_result(self, result: str) -> Dict[str, Any]:
        """Parse the briefing result to extract email and SMS portions."""
        email_briefing = result
        sms_summary = ""

        # Try to find SMS section
        if "## SMS" in result or "SMS SUMMARY" in result:
            parts = result.split("## SMS")
            if len(parts) > 1:
                email_briefing = parts[0].strip()
                sms_part = parts[1].strip()
                # Extract just the SMS message (first line or up to 160 chars)
                sms_lines = sms_part.split("\n")
                for line in sms_lines:
                    line = line.strip()
                    if line and not line.startswith("#"):
                        sms_summary = line[:160]
                        break

        if not sms_summary:
            # Generate a basic SMS summary from the content
            sms_summary = "Check email for daily briefing."

        return {
            "email_briefing": email_briefing,
            "sms_summary": sms_summary,
            "raw_result": result
        }
