@echo off
REM Switch to Supabase environment

echo Switching to Supabase (production)...
copy /Y .env.supabase .env
echo Done! Now using Supabase PostgreSQL
echo.
echo Make sure you've updated DATABASE_URL in .env.supabase with your Supabase connection string
