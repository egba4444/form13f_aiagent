@echo off
REM Railway Deployment Script for Form 13F AI Agent
REM
REM Prerequisites:
REM   1. Railway CLI installed (npm install -g @railway/cli)
REM   2. Logged in to Railway (railway login)
REM   3. Environment variables configured

echo ============================================================
echo Railway Deployment - Form 13F AI Agent
echo ============================================================
echo.

REM Check if logged in
railway whoami >nul 2>&1
if errorlevel 1 (
    echo ❌ Not logged in to Railway!
    echo.
    echo Please run: railway login
    echo Then run this script again.
    exit /b 1
)

echo ✅ Logged in to Railway
echo.

REM Initialize Railway project if needed
if not exist ".railway" (
    echo 📦 Initializing new Railway project...
    railway init
) else (
    echo ✅ Railway project already initialized
)

echo.
echo ============================================================
echo Environment Variables Configuration
echo ============================================================
echo.
echo Setting up environment variables in Railway...
echo.

REM Set environment variables
echo Setting DATABASE_URL...
railway variables --set DATABASE_URL=postgresql://postgres:ispgW1VOhuCsSxvO@db.ocgueuyckdkpedxvbpge.supabase.co:5432/postgres

echo Setting LLM_PROVIDER...
railway variables --set LLM_PROVIDER=anthropic

echo Setting LLM_MODEL...
railway variables --set LLM_MODEL=claude-3-5-sonnet-20241022

echo Setting LLM_MAX_TOKENS...
railway variables --set LLM_MAX_TOKENS=4096

echo Setting LLM_TEMPERATURE...
railway variables --set LLM_TEMPERATURE=0.0

echo Setting LOG_LEVEL...
railway variables --set LOG_LEVEL=INFO

echo Setting ENVIRONMENT...
railway variables --set ENVIRONMENT=production

echo.
echo ⚠️  IMPORTANT: You need to set ANTHROPIC_API_KEY manually!
echo.
echo Run this command with your actual API key:
echo railway variables --set ANTHROPIC_API_KEY=sk-ant-your-actual-key-here
echo.
pause

echo.
echo ============================================================
echo Deploying to Railway
echo ============================================================
echo.

REM Deploy
railway up

echo.
echo ============================================================
echo Deployment Complete!
echo ============================================================
echo.
echo Next steps:
echo   1. Check deployment status: railway status
echo   2. View logs: railway logs
echo   3. Open in browser: railway open
echo   4. Get URL: railway domain
echo.
echo Your API will be available at:
echo   https://your-project.up.railway.app/docs
echo.
