@echo off
echo ========================================
echo      FlagWars Game Server Launcher
echo ========================================
echo.

REM Check if uv is installed
u list >nul 2>&1
if errorlevel 1 (
    echo Installing uv...
    powershell -Command "irm https://astral.sh/uv/install.ps1 | iex"
    echo.
)

REM Check Python environment
echo Checking Python environment...
uv python find >nul 2>&1
if errorlevel 1 (
    echo Installing Python...
    uv python install
    echo.
)

REM Install dependencies
echo Installing game dependencies...
uv sync

REM Start server
echo.
echo Starting FlagWars game server...
echo Server will start at http://localhost:8888
echo Press Ctrl+C to stop the server
echo.

uv run python run_server.py

pause