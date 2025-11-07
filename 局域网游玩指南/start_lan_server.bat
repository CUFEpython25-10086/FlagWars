@echo off
echo ====================================
echo FlagWars 局域网游戏服务器启动器
echo ====================================
echo.

echo 正在检查 Python 环境...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo 错误: 未找到 Python，请先安装 Python 3.8 或更高版本
    pause
    exit /b 1
)

echo 正在检查 uv 包管理器...
uv --version >nul 2>&1
if %errorlevel% neq 0 (
    echo 错误: 未找到 uv 包管理器，请先安装 uv
    echo 安装命令: powershell -Command "irm https://astral.sh/uv/install.ps1 | iex"
    pause
    exit /b 1
)

echo 正在检查项目依赖...
if not exist "uv.lock" (
    echo 错误: 未找到项目依赖文件，请确保在项目根目录运行此脚本
    pause
    exit /b 1
)

echo 正在安装/更新依赖...
uv sync

echo.
echo 正在启动 FlagWars 游戏服务器...
echo 服务器将监听在所有网络接口上，局域网内其他设备可以访问
echo.

echo 获取本机 IP 地址...
for /f "tokens=2 delims=:" %%a in ('ipconfig ^| findstr /i "IPv4"') do set LOCAL_IP=%%a
set LOCAL_IP=%LOCAL_IP: =%

echo.
echo ====================================
echo 服务器已启动！
echo ====================================
echo.
echo 本机访问地址: http://localhost:8888
echo 局域网访问地址: http://%LOCAL_IP%:8888
echo.
echo 请将局域网访问地址分享给其他玩家
echo 其他玩家只需在浏览器中输入该地址即可加入游戏
echo.
echo 按 Ctrl+C 停止服务器
echo.

uv run python run_server.py

pause