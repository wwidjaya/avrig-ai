param(
    [Parameter(Mandatory = $true, Position = 0)]
    [ValidateSet("add", "query", "delete")]
    [string]$Action,

    [Parameter(Mandatory = $true, Position = 1)]
    [string]$Name,

    [Parameter(Position = 2)]
    [string]$Data = "",

    [Parameter(Mandatory = $true)]
    [ValidateNotNullOrEmpty()]
    [string]$Zone,

    [string]$WslDist = "avrig-ai",
    [string]$Server = "wirianto-zb.avrig.ai",
    [string]$Admin = "Administrator",
    [string]$Type = ""
)

$ErrorActionPreference = "Stop"

if ([string]::IsNullOrWhiteSpace($WslDist)) { throw "WslDist must identify the target WSL distribution." }
if ([string]::IsNullOrWhiteSpace($Server)) { throw "Server must identify the Samba DNS server." }
if ([string]::IsNullOrWhiteSpace($Admin)) { throw "Admin must identify the Samba account." }

$Zone = $Zone.TrimEnd('.').ToLowerInvariant()
$Name = $Name.TrimEnd('.')
if ([string]::IsNullOrWhiteSpace($Zone) -or [string]::IsNullOrWhiteSpace($Name)) {
    throw "Zone and Name must not be empty."
}

# Samba record names are relative to the selected zone. Accept an FQDN only
# when it belongs to that zone, then normalize it to a relative name.
if ($Name.Contains('.')) {
    $suffix = "." + $Zone
    if (-not $Name.EndsWith($suffix, [StringComparison]::OrdinalIgnoreCase)) {
        throw "FQDN '$Name' is outside zone '$Zone'. Pass a zone-relative name or an FQDN in that zone."
    }
    $Name = $Name.Substring(0, $Name.Length - $suffix.Length)
}
if ([string]::IsNullOrWhiteSpace($Name)) { $Name = "@" }

switch ($Action) {
    "add" {
        if ([string]::IsNullOrWhiteSpace($Type)) { $Type = "A" }
        if ([string]::IsNullOrWhiteSpace($Data)) { throw "add requires explicit record data. No IP default is assumed." }
    }
    "query" {
        if ([string]::IsNullOrWhiteSpace($Type)) { $Type = "A" }
    }
    "delete" {
        if ([string]::IsNullOrWhiteSpace($Type)) { $Type = "A" }
        if ([string]::IsNullOrWhiteSpace($Data)) { throw "delete requires the exact record data to remove." }
    }
}

# Check if a root-protected password file exists in WSL for automated non-interactive execution
$checkPwCmd = "if [ -r /root/avrig-ai-secrets/samba-admin-password ]; then echo 'HAS_PW_FILE'; fi"
$hasPw = & wsl.exe -d $WslDist -u root -- bash -c $checkPwCmd 2>$null

if ($hasPw -match "HAS_PW_FILE") {
    # Execute with credentials file via python runner to prevent shell expansion issues
    $pyRunner = @"
import subprocess, sys

with open('/root/avrig-ai-secrets/samba-admin-password') as f:
    pw = f.read().strip()

cmd = ['samba-tool', 'dns', '$Action', '$Server', '$Zone', '$Name', '$Type']
data = '$Data'.strip()
if data:
    cmd.append(data)
cmd.extend(['-U', '$Admin', f'--password={pw}', '--use-kerberos=off'])

res = subprocess.run(cmd)
sys.exit(res.returncode)
"@
    Write-Host "Samba DNS ${Action}: zone=$Zone name=$Name type=$Type server=$Server distro=$WslDist (authenticated via root credentials store)"
    & wsl.exe -d $WslDist -u root -- python3 -c $pyRunner
} else {
    # Invoke wsl.exe directly with individual arguments and let caller authenticate
    $wslArgs = @("-d", $WslDist, "--", "samba-tool", "dns", $Action, $Server, $Zone, $Name, $Type)
    if (-not [string]::IsNullOrWhiteSpace($Data)) { $wslArgs += $Data }
    $wslArgs += @("-U", $Admin, "--use-kerberos=required")

    Write-Host "Samba DNS ${Action}: zone=$Zone name=$Name type=$Type server=$Server distro=$WslDist"
    & wsl.exe @wslArgs
}

if ($LASTEXITCODE -ne 0) {
    throw "samba-tool dns $Action failed with exit code $LASTEXITCODE."
}
