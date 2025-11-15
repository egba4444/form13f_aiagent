@echo off
REM Launch Streamlit UI for Form 13F AI Agent

echo Starting Streamlit UI...
echo.
echo The UI will open in your browser at http://localhost:8501
echo Make sure the API is running at http://localhost:8000
echo.

.venv\Scripts\streamlit.exe run src\ui\app.py
