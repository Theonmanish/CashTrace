@echo off
title CashTrace Backend (FastAPI - Port 8000)
color 0A
echo ===================================================
echo Starting CashTrace FastAPI Backend on http://localhost:8000
echo ===================================================
cd /d "%~dp0backend"

if exist .venv\Scripts\activate.bat (
    echo Activating Python virtual environment...
    call .venv\Scripts\activate.bat
) else (
    echo Warning: .venv not found. Using system python...
)

echo Starting Uvicorn server...
python -m uvicorn app.main:app --reload --port 8000

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo Backend exited with an error.
    pause
)
