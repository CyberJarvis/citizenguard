@echo off
REM BlueRadar Social Intelligence - Run Script (Windows)
REM Starts the API server on port 8001

echo ==================================================
echo    BlueRadar Social Intelligence System
echo ==================================================
echo.

REM Change to the SMI module directory
cd /d "%~dp0"

echo Checking for existing processes on port 8001...
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :8001') do taskkill /PID %%a /F >nul 2>&1

echo.
echo Starting API server on http://localhost:8001...
echo.

REM Check if virtual environment exists and activate
if exist "venv\Scripts\activate.bat" (
    call venv\Scripts\activate.bat
)

REM Start the API server
python -m uvicorn api.main:app --host 0.0.0.0 --port 8001 --reload

pause
