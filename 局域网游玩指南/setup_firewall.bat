@echo off
echo ====================================
echo FlagWars Firewall Configuration Script
echo ====================================
echo.

echo This script will add firewall rules to allow other devices to access FlagWars game server
echo.

netsh advfirewall firewall show rule name="FlagWars Server" >nul 2>&1
if %errorlevel% equ 0 (
    echo Firewall rule "FlagWars Server" already exists
    echo Do you want to delete the existing rule and recreate it? (Y/N)
    set /p choice=
    if /i "%choice%"=="Y" (
        echo Deleting existing rule...
        netsh advfirewall firewall delete rule name="FlagWars Server" >nul 2>&1
        echo Existing rule deleted
    ) else (
        echo Keeping existing rule, no reconfiguration needed
        pause
        exit /b 0
    )
)

echo Adding firewall rule...
netsh advfirewall firewall add rule name="FlagWars Server" dir=in action=allow protocol=TCP localport=8888 profile=private >nul 2>&1

if %errorlevel% equ 0 (
    echo.
    echo ====================================
    echo Firewall rule configuration successful!
    echo ====================================
    echo.
    echo Added rule "FlagWars Server", allowing other devices to access game server via TCP port 8888
    echo.
    echo Note: This rule only applies to "Private" network profile
    echo If your network connection is identified as "Public", additional configuration may be needed
    echo.
) else (
    echo.
    echo ====================================
    echo Firewall rule configuration failed!
    echo ====================================
    echo.
    echo Please ensure you are running this script with administrator privileges
    echo Or manually add inbound rule for port 8888 in Windows Firewall settings
    echo.
)

pause