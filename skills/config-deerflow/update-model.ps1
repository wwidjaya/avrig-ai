<#
.SYNOPSIS
    Update DeerFlow model configuration from Windows host.
.DESCRIPTION
    Writes model config and API key to WSL DeerFlow instance. Requires WSL with sudo access.
.EXAMPLE
    .\update-model.ps1 -Name "free" -Use "deerflow.models.patched_openai:PatchedChatOpenAI" -Model "free" -BaseUrl "https://llmrouter.wirianto.ai/v1" -Key "sk-..."
#>
param(
    [Parameter(Mandatory=$true)][string]$Name,
    [Parameter(Mandatory=$true)][string]$Use,
    [Parameter(Mandatory=$true)][string]$Model,
    [Parameter(Mandatory=$true)][string]$BaseUrl,
    [string]$Key = "",
    [string]$Display = "",
    [string]$Display = "",
    [string]$Timeout = "600.0",
    [int]$Retries = 2,
    [int]$MaxTokens = 8192,
    [double]$Temp = 0.7,
    [bool]$Thinking = $true,
    [bool]$Vision = $false,
    [string]$WslInstance = "research",
    [string]$Email = "wwidjaya@gmail.com",
    [string]$Password = "P1a0dRxhEZpQWgYFRae2DaCD"
)

$Display = if ([string]::IsNullOrEmpty($Display)) { $Name } else { $Display }

Write-Host "Updating DeerFlow model '$Name' in WSL '$WslInstance'..." -ForegroundColor Cyan

# Build the WSL command
$wslCmd = @"
sudo bash -c '"'"'(
set -euo pipefail

CONFIG_FILE="/etc/deer-flow/config.yaml"
ENV_FILE="/etc/deer-flow/.env"

# Parse arguments from env vars
NAME="$DF_NAME"
USE="$DF_USE"
MODEL="$DF_MODEL"
BASE_URL="$DF_BASE_URL"
API_KEY="$DF_API_KEY"
DISPLAY_NAME="$DF_DISPLAY"

# Write API key to .env if provided
if [ -n "$API_KEY" ]; then
    env_key_name=\$(echo "$NAME" | tr "[:lower:]" "[:upper:]").replace("-", "_")_API_KEY 
    if grep -q "^${env_key_name}=" "\$ENV_FILE" 2>/dev/null; then
        sed -i "s/^${env_key_name}=.*/${env_key_name}=${API_KEY}/" "\$ENV_FILE"
    else
        echo "${env_key_name}=${API_KEY}" >> "\$ENV_FILE"
    fi
fi

# Update config.yaml using Python
python3 << "PYEOF"
import yaml, os
config_path = "\$CONFIG_FILE"
name = os.environ.get("DF_NAME", "$Name")
use = os.environ.get("DF_USE", "$Use")
model = os.environ.get("DF_MODEL", "$Model")
base_url = os.environ.get("DF_BASE_URL", "$BaseUrl")
api_key = os.environ.get("DF_API_KEY", "$Key")
display_name = os.environ.get("DF_DISPLAY", "$Display")

with open(config_path, "r") as f:
    d = yaml.safe_load(f) or {}
d.setdefault("models", [])

# Check if model exists
existing = next((i for i, m in enumerate(d["models"]) if m.get("name") == name), None)
new_model = {
    "name": name, "display_name": display_name, "use": use, "model": model,
    "api_key": api_key if api_key else (d["models"][existing].get("api_key", "") if existing else ""),
    "base_url": base_url, "request_timeout": 600.0, "max_retries": 2,
    "max_tokens": 8192, "temperature": 0.7, "supports_thinking": True
}

if existing:
    d["models"][existing] = new_model
else:
    d["models"].insert(0, new_model)

d["models"].remove(new_model)
d["models"].insert(0, new_model)

# Set api_key to env var reference if Key provided
if api_key:
    env_key = name.upper().replace("-", "_") + "_API_KEY"
    new_model["api_key"] = "\$" + env_key

with open(config_path, "w") as f:
    yaml.dump(d, f, default_flow_style=False, sort_keys=False)
print(f"Updated model: {name} (default={len(d['models']) > 0 and d['models'][0]['name'] == name})")
PYEOF

# Restart service
systemctl restart deerflow 2>/dev/null || service deerflow restart 2>/dev/null || true
echo "Service restart attempted"
)'"'"' <<< DF_NAME="$Name" DF_USE="$Use" DF_MODEL="$Model" DF_BASE_URL="$BaseUrl" DF_API_KEY="$Key" DF_DISPLAY="$Display"'"'"
'

# Run via wsl
try {
    $result = wsl -d $WslInstance -- bash -c "
        sudo bash -c '
            CONFIG_FILE=\"/etc/deer-flow/config.yaml\"
            ENV_FILE=\"/etc/deer-flow/.env\"
            NAME=\"$Name\"
            USE=\"$Use\"
            MODEL=\"$Model\"
            BASE_URL=\"$BaseUrl\"
            API_KEY=\"$Key\"
            DISPLAY_NAME=\"$Display\"

            if [ -n \"\$API_KEY\" ]; then
                env_key_name=\$(echo \"\$NAME\" | tr \"[:lower:]\" \"[:upper:]\").replace(\"-\", \"_\")_API_KEY 
                if grep -q \"^${env_key_name}=\" \"\$ENV_FILE\" 2>/dev/null; then
                    sed -i \"s/^${env_key_name}=.*/${env_key_name}=\${API_KEY}/\" \"\$ENV_FILE\"
                else
                    echo \"${env_key_name}=\${API_KEY}\" >> \"\$ENV_FILE\"
                fi
            fi

            python3 << PYEOF
import yaml, os
config_path = \"\$CONFIG_FILE\"
name = \"\$NAME\"
use = \"\$USE\"
model = \"\$MODEL\"
base_url = \"\$BASE_URL\"
api_key = \"\$API_KEY\" if \"\$API_KEY\" else \"\"
display_name = \"\$DISPLAY_NAME\" if \"\$DISPLAY_NAME\" else name

with open(config_path, \"r\") as f:
    d = yaml.safe_load(f) or {}
d.setdefault(\"models\", [])

existing = next((i for i, m in enumerate(d[\"models\"]) if m.get(\"name\") == name), None)
new_model = {
    \"name\": name, \"display_name\": display_name, \"use\": use, \"model\": model,
    \"api_key\": api_key if api_key else (d[\"models\"][existing].get(\"api_key\", \"\") if existing else \"\"),
    \"base_url\": base_url, \"request_timeout\": 600.0, \"max_retries\": 2,
    \"max_tokens\": 8192, \"temperature\": 0.7, \"supports_thinking\": True
}

if existing:
    d[\"models\"][existing] = new_model
else:
    d[\"models\"].insert(0, new_model)

d[\"models\"].remove(new_model)
d[\"models\"].insert(0, new_model)

if api_key:
    env_key = name.upper().replace(\"-\", \"_\") + \"_API_KEY\"
    new_model[\"api_key\"] = \"\$\" + env_key

with open(config_path, \"w\") as f:
    yaml.dump(d, f, default_flow_style=False, sort_keys=False)
print(f\"SUCCESS: Model {name} set as default\")
PYEOF

            systemctl restart deerflow
        '
    " 2>&1

    Write-Host $result
} catch {
    Write-Host "ERROR: $_" -ForegroundColor Red
}