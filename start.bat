@echo off
title AIDE Platform Launcher
cls
echo ===================================================
echo             STARTING AIDE PLATFORM                 
echo ===================================================
echo.
echo [1/2] Starting Python Ingestion & Scoring Worker...
start "AIDE Python Pipeline Worker" cmd /k ".\.venv\Scripts\python.exe __main__.py --listen"

echo [2/2] Starting React Broadsheet Frontend...
start "AIDE React Frontend" cmd /k "cd frontend && npm start"

echo.
echo ===================================================
echo  AIDE Platform services launched!
echo  Frontend URL: http://localhost:3000
echo  To stop all services, run stop.bat
echo ===================================================
pause
