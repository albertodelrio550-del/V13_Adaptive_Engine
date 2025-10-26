@echo off
setlocal
cd /d "%~dp0\.."
python scripts\post_validation_reports.py --notify
