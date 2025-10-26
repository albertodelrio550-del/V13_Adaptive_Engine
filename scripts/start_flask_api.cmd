@echo off
setlocal EnableDelayedExpansion
rem -----------------------------------------------------------------------------
rem Flask API local launcher (Docker-free) for Windows
rem - Uses repo-local .venv if present, otherwise any python on PATH
rem - Installs dependencies from flask-api/requirements.txt if needed
rem - Starts Flask app on http://localhost:5000 in a new window
rem -----------------------------------------------------------------------------

rem Resolve repo root (one level up from scripts)
set "SCRIPT_DIR=%~dp0"
pushd "%SCRIPT_DIR%\.."
set "REPO_ROOT=%CD%"
popd

rem Pick Python: prefer repo .venv\Scripts\python.exe, else PATH python
set "PYTHON_EXE="
if exist "%REPO_ROOT%\.venv\Scripts\python.exe" (
  set "PYTHON_EXE=%REPO_ROOT%\.venv\Scripts\python.exe"
) else (
  for /f "delims=" %%P in ('where python 2^>nul') do (
    set "PYTHON_EXE=%%P"
    goto :PY_FOUND
  )
)

:PY_FOUND
if not defined PYTHON_EXE (
  echo [ERROR] Python not found.
  echo Install Python 3.11+ and add it to PATH, or create a virtualenv at:
  echo   %REPO_ROOT%\.venv
  pause
  exit /b 1
)

echo Using Python: "%PYTHON_EXE%"
"%PYTHON_EXE%" --version

rem Ensure pip is available and install deps
echo.
echo Ensuring Flask dependencies are installed...
"%PYTHON_EXE%" -m pip --version >nul 2>&1
if errorlevel 1 (
  echo [INFO] Installing pip...
  "%PYTHON_EXE%" -m ensurepip --upgrade
)

"%PYTHON_EXE%" -m pip install --upgrade pip
"%PYTHON_EXE%" -m pip install -r "%REPO_ROOT%\flask-api\requirements.txt"
if errorlevel 1 (
  echo [ERROR] Failed to install Flask dependencies from requirements.txt
  pause
  exit /b 1
)

echo.
echo Starting Flask API on http://localhost:5000 ...
echo Close the window to stop the server.
start "Flask API" cmd /k "\"%PYTHON_EXE%\" \"%REPO_ROOT%\flask-api\app.py\""

exit /b 0
