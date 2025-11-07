@echo off
echo ====================================
echo FlagWars LAN Game Quick Connect
echo ====================================
echo.

set /p server_ip=Please enter game server IP address: 

if "%server_ip%"=="" (
    echo Error: IP address cannot be empty
    pause
    exit /b 1
)

echo.
echo Attempting to connect to game server...
echo If connection is successful, browser will automatically open the game page
echo.

timeout /t 2 /nobreak >nul

start http://%server_ip%:8888

echo.
echo Browser has been opened, if the game page does not load correctly, please check:
echo 1. Whether the server IP address is correct
echo 2. Whether the game server is running
echo 3. Whether firewall settings are correct
echo 4. Whether network connection is normal
echo.

pause