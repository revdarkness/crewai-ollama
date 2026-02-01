"""
CrewAI Agent Swarm using Ollama Cloud Models

This module defines a crew of AI agents that collaborate on tasks,
powered by Ollama Cloud models like Kimi K2.5 and DeepSeek V3.1.
"""

import os
from crewai import Agent, Crew, Process, Task, LLM
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure Ollama LLM
# CrewAI uses LiteLLM format: "ollama/model_name"
def get_ollama_llm(model: str = None) -> LLM:
    """Create an Ollama LLM instance for CrewAI agents."""
    model_name = model or os.getenv("OLLAMA_MODEL", "kimi-k2.5:cloud")
    ollama_host = os.getenv("OLLAMA_HOST", "http://localhost:11434")

    return LLM(
        model=f"ollama/{model_name}",
        base_url=ollama_host,
        temperature=0.7,
    )


# =============================================================================
# AGENT DEFINITIONS
# =============================================================================

def create_researcher(llm: LLM = None) -> Agent:
    """Create a research specialist agent."""
    return Agent(
        role="Senior Research Analyst",
        goal="Uncover cutting-edge developments and insights on the given topic",
        backstory="""You are a seasoned researcher with a passion for discovering
        the latest trends and breakthroughs. You have a keen eye for detail and
        excel at synthesizing complex information into clear insights.""",
        verbose=True,
        allow_delegation=False,
        llm=llm or get_ollama_llm(),
    )


def create_writer(llm: LLM = None) -> Agent:
    """Create a content writer agent."""
    return Agent(
        role="Content Strategist",
        goal="Craft compelling and informative content based on research findings",
        backstory="""You are a skilled writer who transforms complex topics into
        engaging narratives. You have years of experience creating content that
        resonates with diverse audiences.""",
        verbose=True,
        allow_delegation=False,
        llm=llm or get_ollama_llm(),
    )


def create_analyst(llm: LLM = None) -> Agent:
    """Create a data analyst agent."""
    return Agent(
        role="Data Analyst",
        goal="Analyze information and provide data-driven recommendations",
        backstory="""You are an analytical expert who excels at finding patterns
        and extracting meaningful insights from data. Your recommendations are
        always backed by solid evidence.""",
        verbose=True,
        allow_delegation=False,
        llm=llm or get_ollama_llm(),
    )


def create_coordinator(llm: LLM = None) -> Agent:
    """Create a project coordinator agent (manager for hierarchical crews)."""
    return Agent(
        role="Project Coordinator",
        goal="Coordinate team efforts and ensure high-quality deliverables",
        backstory="""You are an experienced project manager who excels at
        orchestrating complex workflows. You know how to leverage each team
        member's strengths to achieve optimal results.""",
        verbose=True,
        allow_delegation=True,
        llm=llm or get_ollama_llm(),
    )


# =============================================================================
# TASK DEFINITIONS
# =============================================================================

def create_research_task(agent: Agent, topic: str) -> Task:
    """Create a research task."""
    return Task(
        description=f"""Conduct comprehensive research on: {topic}

        Your research should include:
        1. Current state and recent developments
        2. Key players and stakeholders
        3. Challenges and opportunities
        4. Future trends and predictions

        Compile your findings into a detailed research brief.""",
        expected_output="A comprehensive research brief with key findings, trends, and insights",
        agent=agent,
    )


def create_analysis_task(agent: Agent, context_task: Task) -> Task:
    """Create an analysis task that depends on research."""
    return Task(
        description="""Analyze the research findings and identify:

        1. Key patterns and correlations
        2. Actionable insights
        3. Risk factors and mitigation strategies
        4. Recommended next steps

        Provide a data-driven analysis report.""",
        expected_output="An analytical report with insights and recommendations",
        agent=agent,
        context=[context_task],
    )


def create_writing_task(agent: Agent, context_tasks: list) -> Task:
    """Create a writing task that synthesizes research and analysis."""
    return Task(
        description="""Based on the research and analysis, create a comprehensive
        report that:

        1. Summarizes key findings in an executive summary
        2. Presents detailed insights with supporting evidence
        3. Provides clear recommendations
        4. Includes a conclusion with next steps

        The report should be well-structured and engaging.""",
        expected_output="A polished, comprehensive report ready for presentation",
        agent=agent,
        context=context_tasks,
    )


# =============================================================================
# CREW CONFIGURATIONS
# =============================================================================

def create_research_crew(topic: str, model: str = None) -> Crew:
    """
    Create a research crew with three agents working sequentially.

    Args:
        topic: The research topic
        model: Ollama model name (default: from env or kimi-k2.5:cloud)

    Returns:
        Configured Crew instance
    """
    llm = get_ollama_llm(model)

    # Create agents
    researcher = create_researcher(llm)
    analyst = create_analyst(llm)
    writer = create_writer(llm)

    # Create tasks
    research_task = create_research_task(researcher, topic)
    analysis_task = create_analysis_task(analyst, research_task)
    writing_task = create_writing_task(writer, [research_task, analysis_task])

    # Create crew
    return Crew(
        agents=[researcher, analyst, writer],
        tasks=[research_task, analysis_task, writing_task],
        process=Process.sequential,
        verbose=True,
    )


def create_hierarchical_crew(topic: str, model: str = None) -> Crew:
    """
    Create a hierarchical crew with a manager coordinating agents.

    Args:
        topic: The research topic
        model: Ollama model name (default: from env or kimi-k2.5:cloud)

    Returns:
        Configured Crew instance with hierarchical process
    """
    llm = get_ollama_llm(model)

    # Create agents
    coordinator = create_coordinator(llm)
    researcher = create_researcher(llm)
    analyst = create_analyst(llm)
    writer = create_writer(llm)

    # Create tasks
    research_task = create_research_task(researcher, topic)
    analysis_task = create_analysis_task(analyst, research_task)
    writing_task = create_writing_task(writer, [research_task, analysis_task])

    # Create hierarchical crew
    return Crew(
        agents=[researcher, analyst, writer],
        tasks=[research_task, analysis_task, writing_task],
        manager_agent=coordinator,
        process=Process.hierarchical,
        verbose=True,
    )


# Available Ollama Cloud models
OLLAMA_CLOUD_MODELS = {
    "kimi": "kimi-k2.5:cloud",
    "deepseek": "deepseek-v3.1:671b-cloud",
}

# Available local models
OLLAMA_LOCAL_MODELS = {
    "llama3": "llama3:latest",
    "dolphin": "dolphin-llama3:8b",
    "nemotron": "nemotron:latest",
    "codegemma": "codegemma:latest",
}
