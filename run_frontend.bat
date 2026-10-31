@echo off
title CashTrace Frontend (Next.js - Port 3000)
color 0B
echo ===================================================
echo Starting CashTrace Next.js Frontend on http://localhost:3000
echo ===================================================
cd /d "%~dp0frontend"

npm run dev

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo Frontend exited with an error.
    pause
)
