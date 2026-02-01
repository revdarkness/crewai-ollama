# Teaching Assistant Crew

An AI-powered teaching assistant built with [CrewAI](https://crewai.com) and [Ollama](https://ollama.ai), designed to help teachers stay organized with daily briefings, schedule management, and milestone tracking.

## Features

- **Daily Briefings** - Automated morning emails summarizing your day
- **Schedule Analysis** - Reads Google Calendar to identify teaching blocks and prep windows
- **Milestone Tracking** - Monitors upcoming deadlines and flags risks
- **Email Commands** - Add nudges, notes, and milestones via email triggers
- **SMS Summaries** - Optional Twilio integration for quick mobile alerts
- **Local LLM Support** - Runs on Ollama with models like Llama 3, or cloud models like Kimi K2.5

## Architecture

### Agent Crew (Sequential Workflow)

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│ Schedule Reader │ ──▶ │  Project Pulse  │ ──▶ │ Nudge Composer  │
│                 │     │    Analyst      │     │                 │
│ • Parse calendar│     │ • Track miles-  │     │ • Email briefing│
│ • Find prep gaps│     │   tones         │     │ • SMS summary   │
│ • Flag conflicts│     │ • Flag risks    │     │ • Prioritize    │
└─────────────────┘     └─────────────────┘     └─────────────────┘
```

| Agent | Role | Temperature |
|-------|------|-------------|
| **Schedule Reader** | Analyzes today's calendar events | 0.3 |
| **Project Pulse** | Tracks milestones, identifies risks | 0.4 |
| **Nudge Composer** | Creates briefings and summaries | 0.6 |

### Integrations

- **Google Calendar** - Teaching schedule and project milestones
- **Gmail IMAP** - Trigger email ingestion
- **SMTP** - Email notifications
- **Twilio** - SMS alerts (optional)
- **SQLite** - Local database for nudges, notes, and logs

## Installation

### Prerequisites

- Python 3.10-3.13
- [Ollama](https://ollama.ai) running locally (or cloud API access)
- Google Cloud project with Calendar API enabled

### Setup

1. **Clone the repository**
   ```bash
   git clone https://github.com/revdarkness/crewai-ollama.git
   cd crewai-ollama
   ```

2. **Create a virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -e .
   ```

4. **Configure environment**
   ```bash
   cp .env.example .env
   # Edit .env with your credentials
   ```

5. **Set up Google Calendar**
   - Create a project in [Google Cloud Console](https://console.cloud.google.com)
   - Enable the Google Calendar API
   - Create OAuth 2.0 credentials and download as `credentials.json`
   - Place `credentials.json` in the project root

6. **Initialize the database**
   ```bash
   python -m ollama_swarm.main --init-db
   ```

## Configuration

Edit `.env` with your settings:

```env
# Ollama
OLLAMA_HOST=http://localhost:11434
OLLAMA_MODEL=llama3:latest

# Google Calendar
GCAL_CALENDAR_ID_SCHEDULE=primary
GCAL_CALENDAR_ID_PROJECTS=primary

# Gmail IMAP (for trigger emails)
IMAP_HOST=imap.gmail.com
IMAP_USER=your_email@gmail.com
IMAP_PASS=your_app_password
IMAP_LABEL=TA-TRIGGERS

# SMTP (for sending emails)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your_email@gmail.com
SMTP_PASS=your_app_password
NOTIFY_EMAIL_TO=your_email@gmail.com

# Twilio SMS (optional)
TWILIO_ACCOUNT_SID=ACxxxxxxxx
TWILIO_AUTH_TOKEN=xxxxxxxx
TWILIO_FROM=+1XXXXXXXXXX
TWILIO_TO=+1XXXXXXXXXX
```

### Gmail App Password

To use Gmail IMAP/SMTP:
1. Enable 2-Factor Authentication on your Google account
2. Go to [App Passwords](https://myaccount.google.com/apppasswords)
3. Generate a new app password for "Mail"
4. Use this 16-character password in your `.env`

## Usage

### Operating Modes

**Daily Briefing** (run at 6 AM via scheduler)
```bash
python -m ollama_swarm.main --mode teacher_daily
```

**Email Ingest** (poll every 10-15 minutes)
```bash
python -m ollama_swarm.main --mode email_ingest
```

**Test Mode** (mock data, no API calls)
```bash
python -m ollama_swarm.main --test
```

### Windows Quick Run

```batch
run.bat daily    # Run daily briefing
run.bat ingest   # Run email ingest
run.bat test     # Test with mock data
```

### Email Commands

Send emails to your configured Gmail with these subject prefixes:

| Subject Prefix | Action | Example |
|----------------|--------|---------|
| `NUDGE:` | Add a reminder | `NUDGE: Grade essays by Friday` |
| `MILESTONE:` | Add calendar milestone | `MILESTONE: Project presentations March 15` |
| `NOTE:` | Save a note | `NOTE: Student X struggling with chapter 5` |
| `TODAY?` | Get quick status | `TODAY?` |

## Project Structure

```
crewai-ollama/
├── src/ollama_swarm/
│   ├── agents/
│   │   ├── schedule_reader.py   # Calendar analysis agent
│   │   ├── project_pulse.py     # Milestone tracking agent
│   │   ├── nudge_composer.py    # Briefing generation agent
│   │   └── teaching_crew.py     # Crew orchestration
│   ├── integrations/
│   │   ├── google_calendar.py   # Google Calendar API
│   │   ├── gmail_imap.py        # Email ingestion
│   │   ├── smtp_sender.py       # Email sending
│   │   └── twilio_sms.py        # SMS notifications
│   ├── database/
│   │   └── db.py                # SQLite database
│   └── main.py                  # Entry point
├── .env.example                 # Environment template
├── pyproject.toml               # Project configuration
└── run.bat                      # Windows runner
```

## Supported Models

### Local (Ollama)
- `llama3:latest` (default)
- `dolphin-llama3:8b`
- `nemotron:latest`
- `codegemma:latest`

### Cloud (via Ollama)
- `kimi-k2.5:cloud`
- `deepseek-v3.1:671b-cloud`

Change the model in `.env`:
```env
OLLAMA_MODEL=kimi-k2.5:cloud
```

## Scheduling

For automated daily briefings, set up a scheduled task:

### Windows Task Scheduler
```batch
schtasks /create /tn "TeachingAssistant" /tr "C:\path\to\run.bat daily" /sc daily /st 06:00
```

### Linux/macOS Cron
```bash
0 6 * * * cd /path/to/crewai-ollama && python -m ollama_swarm.main --mode teacher_daily
```

## License

MIT

## Acknowledgments

- [CrewAI](https://crewai.com) - Multi-agent orchestration framework
- [Ollama](https://ollama.ai) - Local LLM runtime
- [LiteLLM](https://litellm.ai) - LLM API abstraction
