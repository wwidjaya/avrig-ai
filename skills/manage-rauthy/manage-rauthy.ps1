<#
.SYNOPSIS
    Manages Rauthy IAM configuration, themes, templates, and service lifecycle on WSL instance avrig-ai.
.DESCRIPTION
    Wraps inspect, config check, theme styling, cache-busting, and service management for Rauthy IAM (https://iam.avrig.ai).
.PARAMETER Action
    Action to perform: status, logs, config, test, reload-nginx, restart, update-theme
.EXAMPLE
    .\manage-rauthy.ps1 status
    .\manage-rauthy.ps1 update-theme -CssPath "D:\Cloud\OneDrive\AI\Agentic\avrig-ai\apps\web\public\avrig-rauthy-theme.css"
#>

[CmdletBinding()]
param(
    [Parameter(Position = 0, Mandatory = $true)]
    [ValidateSet('status', 'logs', 'config', 'test', 'reload-nginx', 'restart', 'update-theme')]
    [string]$Action,

    [Parameter(Mandatory = $false)]
    [string]$CssPath,

    [Parameter(Mandatory = $false)]
    [string]$Distro = 'avrig-ai'
)

$ErrorActionPreference = 'Stop'

function Invoke-WslBash([string]$Command, [switch]$Root) {
    $uArg = if ($Root) { @('-u', 'root') } else { @() }
    & wsl.exe -d $Distro @uArg -- bash -lc "$Command"
}

switch ($Action) {
    'status' {
        Write-Host "=== Rauthy Service Status ($Distro) ===" -ForegroundColor Cyan
        Invoke-WslBash 'systemctl status rauthy.service --no-pager -l'
        Write-Host "`n=== Nginx Reverse Proxy Status ($Distro) ===" -ForegroundColor Cyan
        Invoke-WslBash 'systemctl status nginx.service --no-pager -l | head -n 12'
        Write-Host "`n=== Endpoint Health Checks ===" -ForegroundColor Cyan
        Invoke-WslBash "curl -k -s -o /dev/null -w 'iam.avrig.ai HTTP %{http_code}\n' https://127.0.0.1:8443/auth/v1/"
    }

    'logs' {
        Write-Host "=== Rauthy Recent Logs ===" -ForegroundColor Cyan
        Invoke-WslBash 'journalctl -u rauthy.service -n 50 --no-pager'
    }

    'config' {
        Write-Host "=== /etc/rauthy/rauthy.toml ===" -ForegroundColor Cyan
        Invoke-WslBash 'sudo cat /etc/rauthy/rauthy.toml' -Root
    }

    'test' {
        Write-Host "=== Testing Nginx Configuration ===" -ForegroundColor Cyan
        Invoke-WslBash 'sudo nginx -t' -Root
    }

    'reload-nginx' {
        Write-Host "=== Reloading Nginx ===" -ForegroundColor Cyan
        Invoke-WslBash 'sudo nginx -t && sudo systemctl reload nginx' -Root
        Write-Host "Nginx reloaded successfully." -ForegroundColor Green
    }

    'restart' {
        Write-Host "=== Restarting Rauthy Service ===" -ForegroundColor Cyan
        Invoke-WslBash 'sudo systemctl restart rauthy.service' -Root
        Start-Sleep -Seconds 2
        Invoke-WslBash 'systemctl status rauthy.service --no-pager -l'
    }

    'update-theme' {
        $sourceCss = if ($CssPath) { $CssPath } else { "D:\Cloud\OneDrive\AI\Agentic\avrig-ai\apps\web\public\avrig-rauthy-theme.css" }
        if (-not (Test-Path $sourceCss)) {
            throw "Theme stylesheet not found at: $sourceCss"
        }
        Write-Host "Deploying custom theme: $sourceCss -> ${Distro}:/var/www/iam-custom/avrig-rauthy-theme.css..." -ForegroundColor Cyan

        $targetWslPath = "/mnt/" + $sourceCss.Substring(0, 1).ToLower() + "/" + $sourceCss.Substring(3).Replace('\', '/')
        $vStr = (Get-Date -Format 'yyyyMMddHHmmss')
        $updateCmd = @"
set -eu
install -d -m 0755 -o www-data -g www-data /var/www/iam-custom
cp '$targetWslPath' /var/www/iam-custom/avrig-rauthy-theme.css
chown www-data:www-data /var/www/iam-custom/avrig-rauthy-theme.css
chmod 0644 /var/www/iam-custom/avrig-rauthy-theme.css
sed -i -E "s/(avrig-rauthy-theme\.css\?v=)[^\"]+/\1$vStr/g" /etc/nginx/sites-available/iam.avrig.ai.conf
nginx -t
systemctl reload nginx
echo "Updated theme cache-bust to v=$vStr and reloaded nginx."
"@
        Invoke-WslBash $updateCmd -Root
        Write-Host "Custom theme deployed and active on https://iam.avrig.ai." -ForegroundColor Green
    }
}
