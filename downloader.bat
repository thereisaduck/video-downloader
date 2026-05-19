@echo off
chcp 65001 >nul
cd /d "%~dp0"

REM Check and auto-install dependencies
echo.
echo ========== Checking Dependencies ==========
python -m pip install -q -r requirements.txt >nul 2>&1

REM Run the main program
echo.
echo ========== Multi-Platform Video Downloader ==========
echo.
python downloader.py %*
pause