@echo off
setlocal enabledelayedexpansion
title EdgeMind AI Studio Launcher
echo ========================================================
echo  EdgeMind AI Studio - Self-Optimizing Image Generator
echo ========================================================
echo.

:: Detect virtual environment if present
if exist "venv\Scripts\activate.bat" (
    echo [*] Activating virtual environment (venv)...
    call "venv\Scripts\activate.bat"
) else if exist ".venv\Scripts\activate.bat" (
    echo [*] Activating virtual environment (.venv)...
    call ".venv\Scripts\activate.bat"
)

:: Validate Python installation
python --version >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [X] Python was not found in PATH!
    echo Please install Python 3.10 or higher and check "Add Python to PATH".
    pause
    exit /b 1
)

:: Ensure dependencies are installed
echo [*] Checking and verifying dependencies...
python -m pip install -r requirements.txt
if %ERRORLEVEL% NEQ 0 (
    echo [!] Warning: Dependency verification encountered warnings. Attempting to start anyway...
)

echo.
echo [*] Starting EdgeMind server on port 7265...
python app.py
pause
