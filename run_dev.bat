@echo off
REM Simple script to run RedRat locally for development

echo Starting RedRat application...
REM Use the top-level app.py instead of app.app module directly
REM This ensures correct imports
python app.py
