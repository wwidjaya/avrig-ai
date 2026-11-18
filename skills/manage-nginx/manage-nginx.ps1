param(
    [Parameter(Mandatory = $true, Position = 0)]
    [ValidateSet("status", "test", "list", "show", "enable", "disable", "reload", "restart", "start", "stop", "logs", "create")]
    [string]$Command,
    [Parameter(Position = 1)]
    [string]$Target = "",
    [Parameter(Position = 2)]
    [string]$Upstream = "",
    [switch]$All,
    [int]$Lines = 50
)

$WslDist = "research"
$SiteDir = "/etc/nginx/sites-available"
$EnabledDir = "/etc/nginx/sites-enabled"
$SslDir = "/etc/nginx/ssl"

$ErrorActionPreference = "Stop"

function Invoke-Wsl([string]$bashCmd, [ValidateSet("show","silent")][string]$mode = "show") {
    $out = wsl -d $WslDist -- bash -lc $bashCmd 2>&1
    if ($LASTEXITCODE -ne 0) {
        Write-Error "wsl command failed (exit $LASTEXITCODE).`n$($out -join "`n")"
        exit 1
    }
    if ($mode -eq "show") {
        return ($out -join "`n")
    }
    return $out
}

switch ($Command) {
    "status" {
        Invoke-Wsl "systemctl status nginx --no-pager -l | head -14"
        Invoke-Wsl "sudo ss -tlnp | grep -E ':80|:443'"
    }
    "test" {
        Invoke-Wsl "sudo nginx -t"
    }
    "list" {
        if ($All) {
            Invoke-Wsl "grep -l server_name $SiteDir/* | xargs -I{} basename {}"
        } else {
            Invoke-Wsl "ls -1 $EnabledDir/"
        }
    }
    "show" {
        if ([string]::IsNullOrWhiteSpace($Target)) {
            Write-Error "show requires a site name, e.g. vector.wirianto.ai"
            exit 1
        }
        Invoke-Wsl "cat $SiteDir/$Target"
    }
    "enable" {
        if ([string]::IsNullOrWhiteSpace($Target)) {
            Write-Error "enable requires a site name, e.g. vector.wirianto.ai"
            exit 1
        }
        Invoke-Wsl "test -f $SiteDir/$Target && sudo ln -sf $SiteDir/$Target $EnabledDir/$Target && sudo nginx -t && sudo systemctl reload nginx"
        Write-Host "Enabled + reloaded: $Target"
    }
    "disable" {
        if ([string]::IsNullOrWhiteSpace($Target)) {
            Write-Error "disable requires a site name, e.g. vector.wirianto.ai"
            exit 1
        }
        if ((Invoke-Wsl "test -e $EnabledDir/$Target && echo yes || echo no" "silent" | Out-String).Trim() -ne "yes") {
            Write-Host "Not enabled: $Target"
            exit 0
        }
        Invoke-Wsl "sudo rm $EnabledDir/$Target && sudo systemctl reload nginx"
        Write-Host "Disabled + reloaded: $Target"
    }
    "reload" { Invoke-Wsl "sudo nginx -t && sudo systemctl reload nginx" }
    "restart" { Invoke-Wsl "sudo nginx -t && sudo systemctl restart nginx" }
    "start" { Invoke-Wsl "sudo systemctl start nginx" }
    "stop" { Invoke-Wsl "sudo systemctl stop nginx" }
    "logs" {
        if ([string]::IsNullOrWhiteSpace($Target)) {
            Invoke-Wsl "sudo tail -n $Lines /var/log/nginx/error.log"
        } else {
            Invoke-Wsl "sudo tail -n $Lines /var/log/nginx/error.log | grep $Target || true"
        }
    }
    "create" {
        if ([string]::IsNullOrWhiteSpace($Target) -or [string]::IsNullOrWhiteSpace($Upstream)) {
            Write-Error "create requires <fqdn> <upstream>, e.g.: create pa.wirianto.ai 172.26.0.1:42617"
            exit 1
        }
        if ($Target -notmatch '\.wirianto\.ai$') {
            Write-Warning "FQDN '$Target' does not end in '.wirianto.ai'. Continuing anyway."
        }
        $crt  = "$SslDir/$Target.crt"
        $key  = "$SslDir/$Target.key"
        $ca   = "$SslDir/wirianto-ca.crt"
        $conf = @"
server {
    listen 80;
    listen [::]:80;
    server_name $Target;
    return 301 https://`$server_name`$request_uri;
}

server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name $Target;

    ssl_certificate     $crt;
    ssl_certificate_key $key;
    ssl_trusted_certificate $ca;

    location / {
        proxy_pass http://$Upstream;
        proxy_http_version 1.1;
        include /etc/nginx/proxy_params;
        proxy_set_header Upgrade `$http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_buffering off;
        proxy_cache off;
    }
}
"@

        $missing = Invoke-Wsl "for f in $crt $key $ca; do test -f `$f || echo `$f; done" "silent"
        $missingClean = (($missing | Out-String).Trim())
        if (-not [string]::IsNullOrWhiteSpace($missingClean)) {
            Write-Error "Missing cert files required for $Target`: $missingClean"
            Write-Error "Mint them first with the issue-cert skill (installs into $SslDir), then re-run create."
            exit 1
        }

        $hadExisting = ((Invoke-Wsl "test -f $SiteDir/$Target && echo yes || echo no" "silent") | Out-String).Trim() -eq "yes"
        if ($hadExisting) {
            Invoke-Wsl "sudo cp -f $SiteDir/$Target $SiteDir/$Target.bak && echo BACKUP" "silent" | Out-Null
            Write-Host "Backed up existing vhost -> $SiteDir/$Target.bak"
        }

        $b64 = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($conf))
        Invoke-Wsl "echo '$b64' | base64 -d | sudo tee $SiteDir/$Target >/dev/null" "silent"

        $testOut = wsl -d $WslDist -- bash -lc "sudo nginx -t" 2>&1
        if ($LASTEXITCODE -ne 0) {
            Invoke-Wsl "sudo rm -f $SiteDir/$Target" "silent"
            if ($hadExisting) {
                Invoke-Wsl "sudo cp -f $SiteDir/$Target.bak $SiteDir/$Target" "silent"
            }
            Write-Error "nginx -t failed; vhost rolled back.`n$($testOut -join "`n")"
            exit 1
        }

        Invoke-Wsl "sudo ln -sf $SiteDir/$Target $EnabledDir/$Target && sudo systemctl reload nginx"
        Write-Host "Created + enabled + reloaded: $Target"
        Write-Host "  vhost:  $SiteDir/$Target"
        Write-Host "  proxy:  http://$Upstream"
    }
}