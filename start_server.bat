@echo off
echo ========================================
echo      FlagWars 游戏服务器启动脚本
echo ========================================
echo.

REM 检查uv是否安装
u list >nul 2>&1
if errorlevel 1 (
    echo 正在安装uv...
    powershell -Command "irm https://astral.sh/uv/install.ps1 | iex"
    echo.
)

REM 检查Python环境
echo 检查Python环境...
uv python find >nul 2>&1
if errorlevel 1 (
    echo 正在安装Python...
    uv python install
    echo.
)

REM 安装依赖
echo 安装游戏依赖...
uv sync

REM 启动服务器
echo.
echo 启动FlagWars游戏服务器...
echo 服务器将在 http://localhost:8888 启动
echo 按 Ctrl+C 停止服务器
echo.

uv run python run_server.py

pause