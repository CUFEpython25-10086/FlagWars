# ====================================
# FlagWars Firewall Configuration Script (PowerShell Version)
# ====================================

Write-Host "====================================" -ForegroundColor Green
Write-Host "FlagWars Firewall Configuration Script" -ForegroundColor Green
Write-Host "====================================" -ForegroundColor Green
Write-Host ""

Write-Host "This script will add firewall rules to allow other devices to access the FlagWars game server"
Write-Host ""

# Check if running with administrator privileges
if (-NOT ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole] "Administrator")) {
    Write-Host "Error: Please run this script with administrator privileges!" -ForegroundColor Red
    Write-Host "Right-click on PowerShell icon and select 'Run as administrator'" -ForegroundColor Yellow
    Write-Host ""
    pause
    exit 1
}

# Check if firewall rule already exists
try {
    $existingRule = Get-NetFirewallRule -DisplayName "FlagWars Server" -ErrorAction SilentlyContinue
    
    if ($existingRule) {
        Write-Host "Firewall rule 'FlagWars Server' already exists" -ForegroundColor Yellow
        $choice = Read-Host "Do you want to delete the existing rule and recreate it? (Y/N)"
        
        if ($choice -eq "Y" -or $choice -eq "y") {
            Write-Host "Deleting existing rule..." -ForegroundColor Yellow
            Remove-NetFirewallRule -DisplayName "FlagWars Server" -ErrorAction SilentlyContinue
            Write-Host "Existing rule deleted" -ForegroundColor Green
        } else {
            Write-Host "Keeping existing rule, no reconfiguration needed" -ForegroundColor Green
            Write-Host ""
            pause
            exit 0
        }
    }
} catch {
    Write-Host "Error checking existing rule: $($_.Exception.Message)" -ForegroundColor Red
}

Write-Host "Adding firewall rule..." -ForegroundColor Yellow

try {
    # Use New-NetFirewallRule to create firewall rule
    New-NetFirewallRule -DisplayName "FlagWars Server" `
                        -Direction Inbound `
                        -Action Allow `
                        -Protocol TCP `
                        -LocalPort 8888 `
                        -Profile Private `
                        -Description "Allow other devices to access FlagWars game server via TCP port 8888"
    
    Write-Host ""
    Write-Host "====================================" -ForegroundColor Green
    Write-Host "Firewall rule configuration successful!" -ForegroundColor Green
    Write-Host "====================================" -ForegroundColor Green
    Write-Host ""
    Write-Host "Rule 'FlagWars Server' added successfully, allowing other devices to access the game server via TCP port 8888"
    Write-Host ""
    Write-Host "Note: This rule only applies to 'Private' network profile" -ForegroundColor Yellow
    Write-Host "If your network connection is identified as 'Public', additional configuration may be needed" -ForegroundColor Yellow
    Write-Host ""
    
} catch {
    Write-Host ""
    Write-Host "====================================" -ForegroundColor Red
    Write-Host "Firewall rule configuration failed!" -ForegroundColor Red
    Write-Host "====================================" -ForegroundColor Red
    Write-Host ""
    Write-Host "Error: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host ""
    Write-Host "Please ensure you run this script with administrator privileges" -ForegroundColor Yellow
    Write-Host "Or manually add an inbound rule for port 8888 in Windows Firewall settings" -ForegroundColor Yellow
    Write-Host ""
}

Write-Host "Press any key to continue..." -ForegroundColor Gray
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")