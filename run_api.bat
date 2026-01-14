@echo off
REM Launch FastAPI Backend for Form 13F AI Agent

echo Starting FastAPI Backend Server...
echo.
echo The API will be available at http://localhost:8000
echo API Docs will be at http://localhost:8000/docs
echo.
echo Press CTRL+C to stop
echo.

.venv\Scripts\python.exe scripts\start_api.py
