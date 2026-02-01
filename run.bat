@echo off
REM Teaching Assistant Crew - Quick Run Script
REM Usage: run.bat [mode] [options]
REM
REM Modes:
REM   daily    - Run daily briefing (default)
REM   ingest   - Run email ingest
REM   test     - Run daily briefing with mock data
REM
REM Examples:
REM   run.bat
REM   run.bat daily
REM   run.bat ingest
REM   run.bat test

setlocal

REM Activate conda environment
call "%USERPROFILE%\miniconda3\Scripts\activate.bat" crewai

REM Change to script directory
cd /d "%~dp0"

REM Parse arguments
set MODE=teacher_daily
set EXTRA_ARGS=

if "%1"=="daily" set MODE=teacher_daily
if "%1"=="ingest" set MODE=email_ingest
if "%1"=="test" (
    set MODE=teacher_daily
    set EXTRA_ARGS=--test
)

REM Run the command
echo Running Teaching Assistant Crew - Mode: %MODE%
python -m ollama_swarm.main --mode %MODE% %EXTRA_ARGS% %2 %3 %4

endlocal
