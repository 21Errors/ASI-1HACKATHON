@echo off
setlocal enabledelayedexpansion

cd /d C:\Users\kamog\asihackathon

REM Create directories
if not exist backend mkdir backend
if not exist frontend mkdir frontend

REM Create empty backend files
(
  echo.Backend package initialization
) > backend\__init__.py

REM Copy config content to backend/config.py - will create separately

REM Create empty files
type nul > backend\finder.py
type nul > backend\researcher.py
type nul > backend\web_intel.py
type nul > frontend\index.html
type nul > main.py

REM Display result
echo.
echo ============ STRUCTURE CREATED ============
echo.
dir /B
echo.
echo ---- BACKEND ----
dir /B backend
echo.
echo ---- FRONTEND ----
dir /B frontend
echo.
pause
