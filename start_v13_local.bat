@echo off
echo Starting V13 Local Environment (Docker-free)
echo ============================================

echo Step 1: Ensure Node.js LTS is available for n8n.
echo This launcher will use scripts\start_n8n_local.cmd which prefers a portable Node 20 if present.

echo Step 2: Starting Flask API via scripts\start_flask_api.cmd...
start "" cmd /k "scripts\start_flask_api.cmd"

echo Waiting 5 seconds for Flask to start...
timeout /t 5 >nul

echo Step 3: Starting n8n via scripts\start_n8n_local.cmd...
start "" cmd /k "scripts\start_n8n_local.cmd"

echo Both services should now be running.
echo Flask: http://localhost:5000
echo n8n: http://localhost:5678
echo Press any key to close this window.
pause >nul
