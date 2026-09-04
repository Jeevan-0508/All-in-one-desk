@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0"

set "PY="
py -3 --version >nul 2>&1 && set "PY=py -3"
if not defined PY ( python --version >nul 2>&1 && set "PY=python" )
if not defined PY (
    echo.
    echo Python 3 was not found.
    echo Install it from https://www.python.org/downloads/
    echo Tick "Add python.exe to PATH" in the installer, then run this again.
    echo.
    pause
    exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
    echo First run - setting up. This takes a minute, only happens once.
    %PY% -m venv .venv
    if errorlevel 1 goto failed
    ".venv\Scripts\python.exe" -m pip install --upgrade pip --quiet
    ".venv\Scripts\python.exe" -m pip install -r requirements.txt --quiet
    if errorlevel 1 goto failed
    echo Setup complete.
)

echo Starting All-in-One Desk - close this window to stop it.
".venv\Scripts\python.exe" app.py
exit /b 0

:failed
echo.
echo Setup failed. Scroll up for the error.
pause
exit /b 1
