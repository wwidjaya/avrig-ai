param(
    [Parameter(Mandatory = $true, Position = 0)]
    [string]$Fqdn,
    [string]$Ttl = "2160h",
    [string]$Out = "",
    [switch]$InstallNginx,
    [switch]$Reload
)

$WslDist = "research"
$VaultAddr = "http://127.0.0.1:8202"
$Role = "wirianto-dot-ai"

$ErrorActionPreference = "Stop"

# --- Validate fqdn ---
if ($Fqdn -notmatch '\.wirianto\.ai$') {
    Write-Warning "FQDN '$Fqdn' does not end in '.wirianto.ai'. Continuing anyway."
}

# --- Resolve output dir ---
if ([string]::IsNullOrWhiteSpace($Out)) {
    $Out = (Get-Location).Path
}
if (-not (Test-Path -LiteralPath $Out -PathType Container)) {
    New-Item -ItemType Directory -Path $Out -Force | Out-Null
}

# --- Run vault write inside WSL, capture JSON ---
$cmd = 'export VAULT_ADDR=' + "'" + $VaultAddr + "'" +
       ' && /opt/vault/vault write -format=json pki/issue/' + $Role +
       ' common_name=' + $Fqdn + ' ttl=' + $Ttl
$wslOutRaw = wsl -d $WslDist -- bash -lc $cmd 2>&1
if ($LASTEXITCODE -ne 0 -or -not $wslOutRaw) {
    Write-Error "Vault issue failed (exit $LASTEXITCODE). Output:`n$($wslOutRaw -join "`n")"
    exit 1
}

$json = $wslOutRaw -join "`n"
$obj = $json | ConvertFrom-Json
if (-not $obj.data -or -not $obj.data.certificate) {
    Write-Error "Unexpected Vault response (no data.certificate). Output: $json"
    exit 1
}
$cert = $obj.data.certificate
$key  = $obj.data.private_key
$ca   = $obj.data.ca_chain[0]

# --- Write the three files on Windows ---
$certPath  = Join-Path $Out "$Fqdn.crt"
$keyPath   = Join-Path $Out "$Fqdn.key"
$chainPath = Join-Path $Out "$Fqdn.chain.crt"
Set-Content -LiteralPath $certPath  -Value $cert -NoNewline -Encoding ascii
Set-Content -LiteralPath $keyPath   -Value $key  -NoNewline -Encoding ascii
Set-Content -LiteralPath $chainPath -Value ($cert + "`n" + $ca + "`n") -Encoding ascii

Write-Host "== Certificate issued for $Fqdn =="
Write-Host "  $certPath"
Write-Host "  $keyPath"
Write-Host "  $chainPath"

# --- Optional nginx install ---
if ($InstallNginx -or $Reload) {
    if ($Out -notmatch '^[A-Za-z]:\\') {
        Write-Error "nginx install requires a Windows drive path like 'C:\dir' (got '$Out')."
        exit 1
    }
    $wslOutDir = ('/mnt/' + $Out.Substring(0, 1).ToLower() + '/' + $Out.Substring(2) -replace '\\', '/').TrimEnd('/')
    foreach ($f in @("$Fqdn.crt", "$Fqdn.key", "$Fqdn.chain.crt")) {
        $wslPath = "$wslOutDir/$f"
        $installCmd = "sudo install -o root -g www-data -m 0640 $wslPath /etc/nginx/ssl/$f"
        wsl -d $WslDist -- bash -lc $installCmd
        if ($LASTEXITCODE -ne 0) {
            Write-Error "nginx install failed for $f"
            exit 1
        }
    }
    Write-Host "Installed into /etc/nginx/ssl/ (root:www-data 0640)"

    if ($Reload) {
        wsl -d $WslDist -- bash -lc "sudo nginx -t && sudo systemctl reload nginx"
        if ($LASTEXITCODE -ne 0) {
            Write-Error "nginx -t / reload failed."
            exit 1
        }
        Write-Host "nginx reloaded."
    }
}