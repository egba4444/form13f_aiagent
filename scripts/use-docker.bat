@echo off
REM Switch to Docker local environment

echo Switching to Docker (local development)...
copy /Y .env.local .env
echo Done! Now using Docker PostgreSQL at localhost:5432
echo.
echo To start Docker PostgreSQL:
echo   docker compose up -d postgres
