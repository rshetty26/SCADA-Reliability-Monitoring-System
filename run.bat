@echo off
title SCADA Reliability Monitor
echo.
echo  ============================================
echo   SCADA RELIABILITY MONITOR
echo  ============================================
echo.

echo [1/2] Installing dependencies...
pip install --prefer-binary fastapi "uvicorn[standard]" aiosqlite pydantic --quiet
if %errorlevel% neq 0 (
    echo ERROR: Failed to install dependencies.
    pause
    exit /b 1
)
echo       Done.
echo.

echo [2/2] Starting server on http://localhost:8000
echo       Press Ctrl+C to stop.
echo.

timeout /t 1 /nobreak >nul
start "" "http://localhost:8000"

cd /d "%~dp0backend"
uvicorn main:app --port 8000
