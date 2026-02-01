"""
Schedule Reader Agent for Teaching Assistant Crew.

Reads today's classes from Google Calendar and identifies teaching blocks and prep windows.
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
        temperature=0.3,  # Lower temperature for factual tasks
    )


def create_schedule_reader_agent(llm: LLM = None) -> Agent:
    """
    Create the Schedule Reader Agent.

    This agent is responsible for:
    - Reading today's classes from Google Calendar
    - Identifying teaching blocks and prep windows
    - Summarizing the day's schedule clearly

    Args:
        llm: Optional LLM instance (default: Ollama)

    Returns:
        Configured Agent instance
    """
    return Agent(
        role="Schedule Reader",
        goal="Read and analyze today's teaching schedule to provide a clear overview of classes, prep time, and commitments",
        backstory="""You are an experienced teaching assistant who specializes in
        schedule management for educators. You understand the rhythms of a school day,
        the importance of prep periods, and how to identify potential scheduling issues.

        You excel at:
        - Parsing calendar events into meaningful teaching blocks
        - Identifying gaps that could be used for preparation
        - Noting any unusual schedule patterns or potential conflicts
        - Providing concise, actionable summaries

        You communicate clearly and focus on what matters most to a busy teacher.""",
        verbose=True,
        allow_delegation=False,
        llm=llm or get_ollama_llm(),
    )


# Task templates for this agent
SCHEDULE_ANALYSIS_TASK = """
Analyze today's teaching schedule and provide a structured summary.

Calendar Events:
{events}

IMPORTANT: Only report events that are actually listed above. Do NOT invent or assume any classes or events. If "No events scheduled" is shown, report that there are no classes today.

Please provide:
1. A chronological list of today's teaching blocks with times (only if events exist)
2. Identified prep/planning windows (gaps of 30+ minutes)
3. Any potential issues or notes (back-to-back classes, short turnarounds, etc.)
4. A one-sentence "day at a glance" summary

If there are no events scheduled, simply state: "No classes or events scheduled for today. The entire day is available for planning, preparation, or personal time."

Format your response clearly with headers and bullet points.
"""

SCHEDULE_QUICK_CHECK_TASK = """
Provide a quick status check for today's schedule.

Calendar Events:
{events}

Current Time: {current_time}

Answer briefly:
- What's the next scheduled event?
- How much time until it starts?
- Any immediate prep needed?
"""
