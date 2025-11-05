@echo off
echo ====================================
echo FlagWars 防火墙配置脚本
echo ====================================
echo.

echo 此脚本将添加防火墙规则，允许其他设备访问 FlagWars 游戏服务器
echo.

netsh advfirewall firewall show rule name="FlagWars Server" >nul 2>&1
if %errorlevel% equ 0 (
    echo 防火墙规则 "FlagWars Server" 已存在
    echo 是否要删除现有规则并重新创建？(Y/N)
    set /p choice=
    if /i "%choice%"=="Y" (
        echo 正在删除现有规则...
        netsh advfirewall firewall delete rule name="FlagWars Server" >nul 2>&1
        echo 现有规则已删除
    ) else (
        echo 保留现有规则，无需重新配置
        pause
        exit /b 0
    )
)

echo 正在添加防火墙规则...
netsh advfirewall firewall add rule name="FlagWars Server" dir=in action=allow protocol=TCP localport=8888 profile=private >nul 2>&1

if %errorlevel% equ 0 (
    echo.
    echo ====================================
    echo 防火墙规则配置成功！
    echo ====================================
    echo.
    echo 已添加规则 "FlagWars Server"，允许其他设备通过 TCP 端口 8888 访问游戏服务器
    echo.
    echo 注意: 此规则仅适用于"专用"网络配置文件
    echo 如果您的网络连接被标识为"公用"网络，可能需要额外配置
    echo.
) else (
    echo.
    echo ====================================
    echo 防火墙规则配置失败！
    echo ====================================
    echo.
    echo 请确保以管理员权限运行此脚本
    echo 或者手动在 Windows 防火墙设置中添加端口 8888 的入站规则
    echo.
)

pause