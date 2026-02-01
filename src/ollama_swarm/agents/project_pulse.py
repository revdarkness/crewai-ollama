"""
Project Pulse Agent for Teaching Assistant Crew.

Tracks project milestones and flags risks and upcoming deadlines.
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
        temperature=0.4,
    )


def create_project_pulse_agent(llm: LLM = None) -> Agent:
    """
    Create the Project Pulse Agent.

    This agent is responsible for:
    - Reading upcoming milestones (7-14 days)
    - Cross-checking with notes and nudges
    - Flagging risks and upcoming deadlines
    - Prioritizing what needs attention

    Args:
        llm: Optional LLM instance (default: Ollama)

    Returns:
        Configured Agent instance
    """
    return Agent(
        role="Project Pulse Analyst",
        goal="Monitor project milestones and student work deadlines, identifying risks and priorities to keep the teacher informed and prepared",
        backstory="""You are a detail-oriented project management specialist who
        works with educators running complex project-based classrooms. You understand
        that teachers juggle multiple student projects, each with their own timelines.

        You excel at:
        - Tracking multiple concurrent project timelines
        - Identifying upcoming deadlines that need preparation
        - Spotting risks before they become problems
        - Connecting notes and observations to milestones
        - Prioritizing what truly needs attention vs. what can wait

        You understand the realities of a classroom - not everything goes to plan,
        and teachers need early warning systems, not last-minute surprises.""",
        verbose=True,
        allow_delegation=False,
        llm=llm or get_ollama_llm(),
    )


# Task templates for this agent
MILESTONE_ANALYSIS_TASK = """
Analyze upcoming project milestones and related notes to identify priorities and risks.

Upcoming Milestones (next 14 days):
{milestones}

Active Nudges/Reminders:
{nudges}

Recent Notes:
{notes}

Please provide:
1. PRIORITY ITEMS (next 3 days) - What needs immediate attention?
2. UPCOMING (4-7 days) - What should be on the radar?
3. HORIZON (8-14 days) - What's coming that needs prep?
4. RISK FLAGS - Any concerns based on notes or patterns?
5. CONNECTIONS - Link relevant notes to upcoming milestones

Be specific about dates and actionable in your recommendations.
"""

PROJECT_STATUS_TASK = """
Provide a quick project status summary.

Milestones:
{milestones}

Nudges:
{nudges}

Answer:
- How many projects have deadlines this week?
- What's the most urgent item?
- Any blocked or at-risk items based on notes?
"""
