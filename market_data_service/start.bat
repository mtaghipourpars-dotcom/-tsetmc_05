@echo off
cd /d "%~dp0"
if not exist .env copy .env.example .env
where docker >nul 2>nul
if errorlevel 1 (
 echo Install and start Docker Desktop first.
 pause
 exit /b 1
)
docker compose up -d --build
if errorlevel 1 exit /b 1
echo Open http://localhost:8000/docs
