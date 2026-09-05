@echo off
title AIDE Platform Stopper
cls
echo ===================================================
echo             STOPPING AIDE PLATFORM                 
echo ===================================================
echo.

echo [1/2] Terminating Node.js / React Frontend processes...
powershell -Command "Get-NetTCPConnection -LocalPort 3000 -ErrorAction SilentlyContinue | ForEach-Object { Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue }"
taskkill /FI "WINDOWTITLE eq AIDE React Frontend*" /F /T >nul 2>&1

echo [2/2] Terminating Python Listener Worker processes...
powershell -Command "Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like '*__main__.py*' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }"
taskkill /FI "WINDOWTITLE eq AIDE Python Pipeline Worker*" /F /T >nul 2>&1

echo.
echo ===================================================
echo  All AIDE Platform services stopped successfully!
echo ===================================================
pause
