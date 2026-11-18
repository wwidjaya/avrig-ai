<#
.SYNOPSIS
    Manages HashiCorp Vault server, Vault Proxy, and certificate issuance for avrig-ai.
.DESCRIPTION
    Interacts with Vault running inside the avrig-ai WSL distribution.
    Supports health checking, issuing TLS certificates for avrig.ai via PKI,
    and inspecting the Vault Proxy token.
.PARAMETER Action
    The action to execute: 'health', 'issue-cert', or 'status'.
.PARAMETER Fqdn
    The fully qualified domain name for certificate issuance (e.g., api.avrig.ai).
.PARAMETER Ttl
    Certificate TTL. Defaults to '2160h' (90 days).
#>
param(
    [Parameter(Mandatory = $true, Position = 0)]
    [ValidateSet("health", "issue-cert", "status")]
    [string]$Action,

    [Parameter(Position = 1)]
    [string]$Fqdn = "",

    [string]$Ttl = "2160h",
    [string]$WslDist = "avrig-ai"
)

$ErrorActionPreference = "Stop"

switch ($Action) {
    "health" {
        Write-Host "Checking Vault server health on $WslDist..." -ForegroundColor Cyan
        wsl.exe -d $WslDist -- curl -s http://127.0.0.1:8200/v1/sys/health
        Write-Host "`nChecking Vault Proxy health on $WslDist via https://vault.avrig.ai..." -ForegroundColor Cyan
        wsl.exe -d $WslDist -- curl --cacert /etc/nginx/ssl/avrig-root-ca.crt -s https://vault.avrig.ai/v1/sys/health
    }
    "status" {
        Write-Host "Checking systemd service status on $WslDist..." -ForegroundColor Cyan
        wsl.exe -d $WslDist -- systemctl status vault vault-proxy --no-pager
    }
    "issue-cert" {
        if ([string]::IsNullOrWhiteSpace($Fqdn)) {
            throw "Fqdn parameter is required for action 'issue-cert'."
        }
        if (-not $Fqdn.EndsWith(".avrig.ai") -and $Fqdn -ne "avrig.ai") {
            throw "FQDN '$Fqdn' must end with .avrig.ai for role avrig-ai-dot-ai."
        }
        Write-Host "Issuing TLS certificate for $Fqdn via Vault PKI on $WslDist..." -ForegroundColor Cyan

        $pyScript = @"
import json, subprocess, sys

recovery_file = "/mnt/d/wsl/avrig-ai/secrets/vault-recovery.txt"
try:
    with open(recovery_file) as f:
        token = json.load(f)["root_token"].strip()
except Exception as e:
    sys.exit(f"Failed to read root token from {recovery_file}: {e}")

payload = json.dumps({
    "common_name": "$Fqdn",
    "alt_names": "localhost",
    "ip_sans": "127.0.0.1,172.26.4.57",
    "ttl": "$Ttl"
})

res = subprocess.run([
    "curl", "-s", "--cacert", "/etc/nginx/ssl/avrig-root-ca.crt",
    "-H", f"X-Vault-Token: {token}",
    "-X", "POST", "-d", payload,
    "https://vault.avrig.ai/v1/pki_avrig_ai/issue/avrig-ai-dot-ai"
], capture_output=True, text=True)

try:
    data = json.loads(res.stdout)["data"]
    cert = data["certificate"]
    chain = "\n".join(data.get("ca_chain", []))
    key = data["private_key"]
    fullchain = f"{cert}\n{chain}\n"
    
    with open(f"/etc/nginx/ssl/$Fqdn.crt", "w") as f_cert:
        f_cert.write(fullchain)
    with open(f"/etc/nginx/ssl/$Fqdn.key", "w") as f_key:
        f_key.write(key.strip() + "\n")
    print(f"Successfully generated /etc/nginx/ssl/$Fqdn.crt and /etc/nginx/ssl/$Fqdn.key")
except Exception as e:
    sys.exit(f"Failed to issue cert: {e}\nResponse: {res.stdout}")
"@
        wsl.exe -d $WslDist -u root -- python3 -c $pyScript
        wsl.exe -d $WslDist -u root -- chmod 0644 "/etc/nginx/ssl/$Fqdn.crt"
        wsl.exe -d $WslDist -u root -- chmod 0600 "/etc/nginx/ssl/$Fqdn.key"
        Write-Host "Verifying issued certificate:" -ForegroundColor Green
        wsl.exe -d $WslDist -- openssl x509 -in "/etc/nginx/ssl/$Fqdn.crt" -noout -subject -issuer -ext subjectAltName
    }
}
