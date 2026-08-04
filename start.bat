@echo off
title EdgeMind AI Studio Launcher
echo ========================================================
echo  EdgeMind AI Studio — Self-Optimizing Image Generator
echo ========================================================
echo.

python -m pip install -r requirements.txt
if %ERRORLEVEL% NEQ 0 (
    echo [!] Warning: Failed installing requirements. Attempting to start anyway...
)

echo Starting EdgeMind server...
python app.py
pause
