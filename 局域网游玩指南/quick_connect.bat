@echo off
echo ====================================
echo FlagWars 局域网游戏快速连接
echo ====================================
echo.

set /p server_ip=请输入游戏服务器IP地址: 

if "%server_ip%"=="" (
    echo 错误: IP地址不能为空
    pause
    exit /b 1
)

echo.
echo 正在尝试连接到游戏服务器...
echo 如果连接成功，浏览器将自动打开游戏页面
echo.

timeout /t 2 /nobreak >nul

start http://%server_ip%:8888

echo.
echo 浏览器已打开，如果游戏页面未正确加载，请检查：
echo 1. 服务器IP地址是否正确
echo 2. 游戏服务器是否正在运行
echo 3. 防火墙设置是否正确
echo 4. 网络连接是否正常
echo.

pause