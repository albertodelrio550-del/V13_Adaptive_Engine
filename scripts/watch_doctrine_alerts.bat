@echo off
setlocal
cd /d "%~dp0\.."
python scripts\doctrine_alerts_cli.py --watch --beep
