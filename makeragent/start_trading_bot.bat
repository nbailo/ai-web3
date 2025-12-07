@echo off
REM ============================================
REM  Autonomous Trading Bot - Startup Script
REM ============================================

echo [1/2] Starting Flask API backend...
start "Trading Bot API" cmd /k "cd /d C:\Users\ishaa && python "Smart Chat Bot.py" --mode api --host 0.0.0.0 --port 8001"

echo [2/2] Starting React UI frontend...
timeout /t 3 /nobreak >nul
start "Trading Bot UI" cmd /k "cd /d C:\Users\ishaa\trading-ui && npm run dev"

echo.
echo ============================================
echo  Both servers are starting in new windows.
echo.
echo  Backend API:  http://localhost:8001
echo  Frontend UI:  http://localhost:5173
echo ============================================
echo.
pause
