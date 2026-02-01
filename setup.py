#!/usr/bin/env python3
"""
Teaching Assistant Crew - Setup and Test Script

This script helps with:
1. Verifying all dependencies are installed
2. Testing connections to required services
3. Initializing the database
4. Running a test with mock data
"""

import os
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from dotenv import load_dotenv
load_dotenv()


def check_dependencies():
    """Check that all required dependencies are installed."""
    print("\n1. Checking Dependencies")
    print("-" * 40)

    deps = {
        "crewai": "CrewAI",
        "litellm": "LiteLLM",
        "dotenv": "python-dotenv",
        "dateutil": "python-dateutil",
    }

    optional_deps = {
        "google.oauth2": "google-auth-oauthlib",
        "googleapiclient": "google-api-python-client",
        "twilio": "twilio",
    }

    all_ok = True

    for module, name in deps.items():
        try:
            __import__(module)
            print(f"  [OK] {name}")
        except ImportError:
            print(f"  [MISSING] {name}")
            all_ok = False

    print("\n  Optional dependencies:")
    for module, name in optional_deps.items():
        try:
            __import__(module)
            print(f"  [OK] {name}")
        except ImportError:
            print(f"  [SKIP] {name} (optional)")

    return all_ok


def check_ollama():
    """Check Ollama connection."""
    print("\n2. Checking Ollama Connection")
    print("-" * 40)

    import requests

    ollama_host = os.getenv("OLLAMA_HOST", "http://localhost:11434")

    try:
        response = requests.get(f"{ollama_host}/api/tags", timeout=5)
        if response.status_code == 200:
            models = response.json().get("models", [])
            print(f"  [OK] Connected to Ollama at {ollama_host}")
            print(f"  [OK] {len(models)} models available")

            # Check for configured model
            model = os.getenv("OLLAMA_MODEL", "llama3:latest")
            model_names = [m.get("name") for m in models]
            if model in model_names:
                print(f"  [OK] Configured model '{model}' is available")
            else:
                print(f"  [WARN] Configured model '{model}' not found")
                print(f"       Available: {', '.join(model_names[:5])}")

            return True
        else:
            print(f"  [FAIL] Unexpected response: {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print(f"  [FAIL] Cannot connect to Ollama at {ollama_host}")
        print("         Make sure Ollama is running: ollama serve")
        return False


def check_env_config():
    """Check environment configuration."""
    print("\n3. Checking Environment Configuration")
    print("-" * 40)

    required = ["OLLAMA_HOST", "OLLAMA_MODEL", "TIMEZONE", "DB_PATH"]
    optional = [
        "IMAP_USER", "IMAP_PASS",
        "SMTP_USER", "SMTP_PASS",
        "TWILIO_ACCOUNT_SID", "TWILIO_AUTH_TOKEN"
    ]

    all_ok = True

    for var in required:
        value = os.getenv(var)
        if value:
            print(f"  [OK] {var} = {value[:30]}...")
        else:
            print(f"  [MISSING] {var}")
            all_ok = False

    print("\n  Optional configuration:")
    for var in optional:
        value = os.getenv(var)
        if value:
            print(f"  [OK] {var} = {'*' * min(len(value), 10)}")
        else:
            print(f"  [SKIP] {var} (not configured)")

    return all_ok


def init_database():
    """Initialize the database."""
    print("\n4. Initializing Database")
    print("-" * 40)

    try:
        from ollama_swarm.database import Database
        db = Database()
        print(f"  [OK] Database initialized: {db.db_path}")

        # Add a test note
        note_id = db.add_note("Setup test note - safe to delete", source="setup")
        print(f"  [OK] Test note added (id: {note_id})")

        return True
    except Exception as e:
        print(f"  [FAIL] Database error: {e}")
        return False


def run_mock_test():
    """Run a quick test with mock data."""
    print("\n5. Running Mock Test")
    print("-" * 40)

    try:
        from ollama_swarm.agents import TeachingAssistantCrew

        # Create crew with local model for speed
        model = os.getenv("OLLAMA_MODEL", "llama3.2:latest")
        print(f"  Creating crew with model: {model}")

        crew = TeachingAssistantCrew(model=model)
        print("  [OK] Crew created successfully")

        # Test quick check
        print("  Running quick check...")
        response = crew.run_quick_check(
            schedule_events=[
                {"summary": "Period 1 - Engineering", "start": "08:00"},
                {"summary": "Period 3 - Robotics", "start": "10:30"},
            ],
            nudges=[
                {"content": "Print rubrics", "priority": "normal"},
            ]
        )

        print("  [OK] Quick check completed")
        print(f"\n  Response preview:\n  {response[:200]}...")

        return True
    except Exception as e:
        print(f"  [FAIL] Test error: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all setup checks."""
    print("=" * 60)
    print("  TEACHING ASSISTANT CREW - Setup & Test")
    print("=" * 60)

    results = []

    results.append(("Dependencies", check_dependencies()))
    results.append(("Ollama", check_ollama()))
    results.append(("Configuration", check_env_config()))
    results.append(("Database", init_database()))

    # Only run mock test if basic checks pass
    if all(r[1] for r in results[:2]):
        results.append(("Mock Test", run_mock_test()))
    else:
        print("\n5. Skipping Mock Test (prerequisites not met)")
        results.append(("Mock Test", False))

    # Summary
    print("\n" + "=" * 60)
    print("  SUMMARY")
    print("=" * 60)

    for name, passed in results:
        status = "PASS" if passed else "FAIL"
        print(f"  {name:20} {status}")

    all_passed = all(r[1] for r in results)

    if all_passed:
        print("\n  All checks passed! Ready to use.")
        print("\n  Quick start:")
        print("    python -m ollama_swarm.main --mode teacher_daily --test")
        print("\n  Or use the batch file:")
        print("    run.bat test")
    else:
        print("\n  Some checks failed. Review the output above.")

    print("")
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
