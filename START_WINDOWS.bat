@echo off
setlocal
cd /d "%~dp0"
where py >nul 2>nul
if not errorlevel 1 (
  py -3 market_data_service\scripts\launch_local.py %*
) else (
  where python >nul 2>nul
  if errorlevel 1 (
    echo Install Python 3.12 from https://www.python.org/downloads/windows/
    echo Enable Add python.exe to PATH. Then run this file again.
    pause
    exit /b 1
  )
  python market_data_service\scripts\launch_local.py %*
)
if errorlevel 1 (
  echo Startup failed. Read the error above.
  pause
  exit /b 1
)
