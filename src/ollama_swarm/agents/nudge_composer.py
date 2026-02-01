"""
Nudge Composer Agent for Teaching Assistant Crew.

Generates daily briefings in both email and SMS formats.
"""

import os
from crewai import Agent, LLM
from typing import Optional


def get_ollama_llm(model: str = None) -> LLM:
    """Create an Ollama LLM instance."""
    model_name = model or os.getenv("OLLAMA_MODEL", "llama3:latest")
    ollama_host = os.getenv("OLLAMA_HOST", "http://localhost:11434")

    return LLM(
        model=f"ollama/{model_name}",
        base_url=ollama_host,
        temperature=0.6,  # Slightly higher for more natural writing
    )


def create_nudge_composer_agent(llm: LLM = None) -> Agent:
    """
    Create the Nudge Composer Agent.

    This agent is responsible for:
    - Synthesizing information from other agents
    - Generating a comprehensive daily briefing email
    - Creating a condensed SMS summary
    - Prioritizing information effectively

    Args:
        llm: Optional LLM instance (default: Ollama)

    Returns:
        Configured Agent instance
    """
    return Agent(
        role="Briefing Composer",
        goal="Create clear, actionable daily briefings that help teachers start their day informed and prepared",
        backstory="""You are a communications specialist who crafts briefings for
        busy professionals. You understand that teachers check their phones early
        in the morning and need information that's immediately useful.

        You excel at:
        - Distilling complex information into clear summaries
        - Prioritizing what matters most at the top
        - Writing in a warm but efficient tone
        - Creating both detailed (email) and ultra-concise (SMS) formats
        - Using formatting that's easy to scan quickly

        You know that a teacher's morning is hectic. Your briefings should reduce
        cognitive load, not add to it. Every word should earn its place.""",
        verbose=True,
        allow_delegation=False,
        llm=llm or get_ollama_llm(),
    )


# Task templates for this agent
DAILY_BRIEFING_TASK = """
Create a daily briefing based on the analyses provided by your teammates.

TODAY'S DATE: {date}

You have received two analyses from your teammates:
1. SCHEDULE ANALYSIS - from the Schedule Reader (review of today's teaching blocks and prep windows)
2. PROJECT STATUS - from the Project Pulse Analyst (milestones, risks, and priorities)

Use the context provided by these previous tasks to create your briefing.

ACTIVE REMINDERS:
{nudges}

Please create TWO outputs:

## EMAIL BRIEFING
Create a well-formatted email briefing with:
- A brief "Day at a Glance" opening (2-3 sentences max)
- Today's Schedule section with times (use the Schedule Reader's analysis)
- Priority Items section (what needs attention TODAY)
- Upcoming Milestones section (next 7 days, from Project Pulse analysis)
- Active Reminders section
- Any notes or observations worth highlighting

Use a professional but warm tone. Be concise but complete.
If there are no classes scheduled today, clearly state that.

## SMS SUMMARY
Create an SMS-length summary (under 160 characters) that captures:
- Number of classes today (0 if none scheduled)
- Most urgent item
- Key milestone if any

Format: "[N] classes today. [urgent item]. [milestone]"
"""

COMPOSE_NUDGE_RESPONSE_TASK = """
Compose a response to a teacher's quick check request.

REQUEST: {request}

CURRENT SCHEDULE:
{schedule}

CURRENT NUDGES:
{nudges}

Write a brief, helpful response that directly answers their question.
Keep it conversational but informative.
"""
