@echo off
setlocal EnableDelayedExpansion
rem -----------------------------------------------------------------------------
rem n8n local (Docker-free) launcher for Windows
rem - Prefers portable Node 20 LTS if available (recommended for n8n)
rem - Falls back to portable Node 22 if present
rem - Installs n8n globally into a repo-local prefix if missing
rem - Loads environment variables from scripts\n8n_local.env (comments supported)
rem - Starts n8n UI on http://localhost:5678
rem -----------------------------------------------------------------------------

rem Resolve repo root (one level up from scripts)
set "SCRIPT_DIR=%~dp0"
pushd "%SCRIPT_DIR%\.."
set "REPO_ROOT=%CD%"
popd

rem Candidate Node portable dirs
set "NODE20_DIR=%REPO_ROOT%\node-v20.18.1-win-x64"
set "NODE22_DIR=%REPO_ROOT%\node-v22.21.0-win-x64"

set "NODE_EXE="
if exist "%NODE20_DIR%\node.exe" (
  set "NODE_EXE=%NODE20_DIR%\node.exe"
) else if exist "%NODE22_DIR%\node.exe" (
  set "NODE_EXE=%NODE22_DIR%\node.exe"
)

if not defined NODE_EXE (
  echo [ERROR] No portable Node.exe found.
  echo Expected one of:
  echo   %NODE20_DIR%\node.exe   ^(preferred, Node 20 LTS^)
  echo   %NODE22_DIR%\node.exe
  echo.
  echo ACTION REQUIRED:
  echo 1^) Download Node.js 20 LTS zip ^(Windows x64^) from:
  echo    https://nodejs.org/dist/latest-v20.x/
  echo 2^) Extract to:
  echo    %REPO_ROOT%\node-v20.18.1-win-x64
  echo 3^) Re-run this script.
  pause
  exit /b 1
)

rem Derive npm path from selected Node
for %%I in ("%NODE_EXE%") do set "NODE_DIR=%%~dpI"
set "NPM_CLI=%NODE_DIR%\node_modules\npm\bin\npm-cli.js"
set "NPM_CMD_EXE=%NODE_DIR%\npm.cmd"
set "USE_NPM_CLI=0"
if exist "%NPM_CLI%" set "USE_NPM_CLI=1"
if not exist "%NPM_CLI%" if not exist "%NPM_CMD_EXE%" (
  echo [ERROR] npm not found next to node.exe:
  echo   %NPM_CLI%
  echo   %NPM_CMD_EXE%
  echo Corrupt or incomplete Node portable? Re-extract Node zip.
  pause
  exit /b 1
)

rem Use a repo-local global prefix to avoid admin rights and PATH pollution
set "GLOBAL_PREFIX=%REPO_ROOT%\node-global"
if not exist "%GLOBAL_PREFIX%" mkdir "%GLOBAL_PREFIX%"

echo.
echo Using Node: "%NODE_EXE%"
"%NODE_EXE%" -v
echo npm path  :
if "%USE_NPM_CLI%"=="1" (
  echo   "%NPM_CLI%"
  "%NODE_EXE%" "%NPM_CLI%" -v
) else (
  echo   "%NPM_CMD_EXE%"
  "%NPM_CMD_EXE%" -v
)
echo Global dir: "%GLOBAL_PREFIX%"
echo.

rem Pin npm prefix to our local directory
if "%USE_NPM_CLI%"=="1" (
  "%NODE_EXE%" "%NPM_CLI%" config set prefix "%GLOBAL_PREFIX%" 1>nul
) else (
  "%NPM_CMD_EXE%" config set prefix "%GLOBAL_PREFIX%" 1>nul
)

rem Check if n8n is already installed in the local-global
echo Checking n8n installation...
if "%USE_NPM_CLI%"=="1" (
  "%NODE_EXE%" "%NPM_CLI%" ls -g n8n | findstr /R /C:"n8n@" >nul
) else (
  "%NPM_CMD_EXE%" ls -g n8n | findstr /R /C:"n8n@" >nul
)
if errorlevel 1 (
  echo Installing n8n globally into "%GLOBAL_PREFIX%" ...
  if "%USE_NPM_CLI%"=="1" (
    "%NODE_EXE%" "%NPM_CLI%" install -g n8n@latest
  ) else (
    "%NPM_CMD_EXE%" install -g n8n@latest
  )
  if errorlevel 1 (
    echo.
    echo [WARN] Latest n8n install failed. Retrying with a known-good version for Node 20...
    if "%USE_NPM_CLI%"=="1" (
      "%NODE_EXE%" "%NPM_CLI%" install -g n8n@1.80.2
    ) else (
      "%NPM_CMD_EXE%" install -g n8n@1.80.2
    )
    if errorlevel 1 (
      echo [ERROR] n8n installation failed. Ensure you are using Node 20 LTS portable.
      echo Tried:
      echo   n8n@latest
      echo   n8n@1.80.2
      pause
      exit /b 1
    )
  )
) else (
  echo n8n is already installed.
)

rem Load environment variables from scripts\n8n_local.env
set "ENV_FILE=%SCRIPT_DIR%n8n_local.env"
if not exist "%ENV_FILE%" (
  echo [ERROR] Missing environment file: %ENV_FILE%
  echo Create it or re-run the setup that generated scripts\n8n_local.env
  pause
  exit /b 1
)

echo.
echo Loading environment from %ENV_FILE%
for /f "usebackq tokens=* delims=" %%L in ("%ENV_FILE%") do (
  set "line=%%L"
  if not "!line!"=="" if "!line:~0,1!" NEQ "#" (
    for /f "tokens=1 delims=#" %%A in ("!line!") do (
      set "clean=%%A"
      for /f "tokens=1* delims==" %%N %%V in ("!clean!") do (
        if not "%%N"=="" if not "%%V"=="" set "%%N=%%V"
      )
    )
  )
)

rem Put our local-global bin on PATH so n8n.cmd is found
set "PATH=%GLOBAL_PREFIX%\bin;%GLOBAL_PREFIX%;%PATH%"

echo.
echo Starting n8n on http://localhost:%N8N_PORT% ...
echo Close the window to stop n8n.
echo.

rem Prefer the shim if available, otherwise execute the JS entry with node
if exist "%GLOBAL_PREFIX%\bin\n8n.cmd" (
  start "n8n" cmd /k "%GLOBAL_PREFIX%\bin\n8n.cmd"
) else (
  set "N8N_BIN=%GLOBAL_PREFIX%\node_modules\n8n\bin\n8n"
  if not exist "%N8N_BIN%" (
    echo [ERROR] Could not locate n8n binary in:
    echo   %GLOBAL_PREFIX%\bin\n8n.cmd
    echo   %GLOBAL_PREFIX%\node_modules\n8n\bin\n8n
    pause
    exit /b 1
  )
  start "n8n" cmd /k "\"%NODE_EXE%\" \"%N8N_BIN%\""
)

exit /b 0
