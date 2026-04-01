@echo off
cd /d "%~dp0"
call venv\Scripts\activate
python voice_assistant.py
pause
