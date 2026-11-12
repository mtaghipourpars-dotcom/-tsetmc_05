@echo off
cd /d "%~dp0"
python scripts\setup_env.py
if errorlevel 1 (
 echo Python 3.12 is needed for setup. Alternatively create .env from .env.example manually.
 exit /b 1
)
where docker >nul 2>nul
if errorlevel 1 (
 echo Install and start Docker Desktop first.
 pause
 exit /b 1
)
docker compose up -d --build
if errorlevel 1 exit /b 1
echo Open http://localhost:8000
