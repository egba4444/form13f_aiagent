@echo off
REM Launch both FastAPI Backend and Streamlit UI

echo ========================================
echo Form 13F AI Agent - Starting All Services
echo ========================================
echo.
echo Starting FastAPI backend and Streamlit UI...
echo.
echo API will be at: http://localhost:8000
echo UI will be at: http://localhost:8501
echo.
echo Keep this window open to keep services running
echo Press CTRL+C to stop all services
echo.

REM Start API in a new window
start "Form 13F API" cmd /k ".venv\Scripts\python.exe scripts\start_api.py"

REM Wait a few seconds for API to start
timeout /t 5 /nobreak >nul

REM Start Streamlit UI in current window
echo Starting Streamlit UI...
.venv\Scripts\streamlit.exe run src\ui\app.py
