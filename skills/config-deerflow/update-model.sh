#!/usr/bin/env bash
set -euo pipefail

# config-deerflow: Update DeerFlow model configuration in /etc/deer-flow/config.yaml
#
# Usage:
#   update-model.sh -n <name> -u <provider_class> -m <model_id> -b <base_url> [-k <api_key>]
#
# Examples:
#   update-model.sh -n free -u deerflow.models.patched_openai:PatchedChatOpenAI -m free -b https://llmrouter.wirianto.ai/v1 -k $LLMROUTER_API_KEY
#   update-model.sh --name deepseek-v4-flash --use langchain_openai:ChatOpenAI --model deepseek-v4-flash --base-url https://api.deepseek.com/v1

CONFIG_FILE="/etc/deer-flow/config.yaml"
ENV_FILE="/etc/deer-flow/.env"

# Defaults
NAME=""
USE=""
MODEL=""
BASE_URL=""
API_KEY=""
DISPLAY_NAME=""
TIMEOUT="600.0"
MAX_RETRIES="2"
MAX_TOKENS="8192"
TEMPERATURE="0.7"
SUPPORTS_THINKING="true"
SUPPORTS_VISION="false"

usage() {
    cat <<EOF
Usage: $0 -n <name> -u <provider_class> -m <model_id> -b <base_url> [-k <api_key>]

Required:
  -n, --name       Internal model name (e.g., free)
  -u, --use        Provider class path (e.g., deerflow.models.patched_openai:PatchedChatOpenAI)
  -m, --model      LLM model ID (e.g., free)
  -b, --base-url   API base URL (e.g., https://llmrouter.wirianto.ai/v1)

Optional:
  -k, --key        API key (if omitted, uses \$LLMROUTER_API_KEY or env var name)
  -d, --display    Display name (defaults to name)
  -t, --timeout    Request timeout (default: 600.0)
  -r, --retries    Max retries (default: 2)
  -T, --max-tokens Max tokens (default: 8192)
  --temp           Temperature (default: 0.7)
  --thinking       Supports thinking (default: true)
  --vision         Supports vision (default: false)
  -h, --help       Show this help

EOF
    exit 1
}

# Parse arguments
while [[ $# -gt 0 ]]; do
    case "$1" in
        -n|--name) NAME="$2"; shift 2 ;;
        -u|--use) USE="$2"; shift 2 ;;
        -m|--model) MODEL="$2"; shift 2 ;;
        -b|--base-url) BASE_URL="$2"; shift 2 ;;
        -k|--key) API_KEY="$2"; shift 2 ;;
        -d|--display) DISPLAY_NAME="$2"; shift 2 ;;
        -t|--timeout) TIMEOUT="$2"; shift 2 ;;
        -r|--retries) MAX_RETRIES="$2"; shift 2 ;;
        -T|--max-tokens) MAX_TOKENS="$2"; shift 2 ;;
        --temp) TEMPERATURE="$2"; shift 2 ;;
        --thinking) SUPPORTS_THINKING="$2"; shift 2 ;;
        --vision) SUPPORTS_VISION="$2"; shift 2 ;;
        -h|--help) usage ;;
        *) echo "Unknown option: $1"; usage ;;
    esac
done

# Validate required fields
if [[ -z "$NAME" || -z "$USE" || -z "$MODEL" || -z "$BASE_URL" ]]; then
    echo "ERROR: -n, -u, -m, -b are required"
    usage
fi

# Default display name to name
if [[ -z "$DISPLAY_NAME" ]]; then
    DISPLAY_NAME="$NAME"
fi

# Build Python script to update config
export DF_NAME="$NAME" DF_USE="$USE" DF_MODEL="$MODEL" DF_BASE_URL="$BASE_URL"
export DF_API_KEY="$API_KEY" DF_DISPLAY="$DISPLAY_NAME" DF_CONFIG_FILE="$CONFIG_FILE"
export DF_ENV_FILE="$ENV_FILE" DF_TIMEOUT="$TIMEOUT" DF_MAX_RETRIES="$MAX_RETRIES"
export DF_MAX_TOKENS="$MAX_TOKENS" DF_TEMPERATURE="$TEMPERATURE"
export DF_THINKING="$SUPPORTS_THINKING" DF_VISION="$SUPPORTS_VISION"

python3 <<'PYEOF'
import yaml, sys, os

config_path = os.environ["DF_CONFIG_FILE"]
env_path = os.environ["DF_ENV_FILE"]
name = os.environ["DF_NAME"]
use = os.environ["DF_USE"]
model = os.environ["DF_MODEL"]
base_url = os.environ["DF_BASE_URL"]
api_key = os.environ["DF_API_KEY"]
display_name = os.environ["DF_DISPLAY"]
timeout = float(os.environ["DF_TIMEOUT"])
max_retries = int(os.environ["DF_MAX_RETRIES"])
max_tokens = int(os.environ["DF_MAX_TOKENS"])
temperature = float(os.environ["DF_TEMPERATURE"])
supports_thinking = (os.environ["DF_THINKING"] == "true")
supports_vision = (os.environ["DF_VISION"] == "true")

# Read existing config
with open(config_path, "r") as f:
    d = yaml.safe_load(f)

if d is None:
    d = {}
if d.get("models") is None:
    d["models"] = []

# Check if model already exists, update or insert
existing = None
for i, m in enumerate(d["models"]):
    if m.get("name") == name:
        existing = i
        break

new_model = {
    "name": name,
    "display_name": display_name,
    "use": use,
    "model": model,
    "api_key": api_key if api_key else d["models"][existing].get("api_key", "") if existing is not None else "",
    "base_url": base_url,
    "request_timeout": timeout,
    "max_retries": max_retries,
    "max_tokens": max_tokens,
    "temperature": temperature,
    "supports_thinking": supports_thinking,
    "supports_vision": supports_vision,
}

if existing is not None:
    d["models"][existing] = new_model
    print(f"Updated model '{name}' in config")
else:
    d["models"].insert(0, new_model)
    print(f"Added model '{name}' to config")

# Move to front (first model is default)
d["models"].remove(new_model)
d["models"].insert(0, new_model)
print(f"Set '{name}' as default (first) model")

# Handle API key env var in .env
if api_key:
    env_key_name = f"{name.upper().replace('-', '_')}_API_KEY"
    # Write to .env
    env_lines = []
    if os.path.exists(env_path):
        with open(env_path, "r") as f:
            lines = f.readlines()
        seen = False
        for line in lines:
            stripped = line.strip()
            # Skip empty lines and comments (keep them)
            if stripped.startswith(f"{env_key_name}="):
                env_lines.append(f"{env_key_name}={api_key}\n")
                seen = True
            else:
                env_lines.append(line)
        if not seen:
            env_lines.append(f"{env_key_name}={api_key}\n")
    else:
        env_lines = [f"{env_key_name}={api_key}\n"]
    
    with open(env_path, "w") as f:
        f.writelines(env_lines)
    print(f"Wrote {env_key_name} to {env_path}")
    
    # Use env var reference in config
    new_model["api_key"] = f"${env_key_name}"
    
    # Re-dump with env var reference
    with open(config_path, "w") as f:
        yaml.dump(d, f, default_flow_style=False, sort_keys=False)
    print(f"Updated config with $" + env_key_name + " reference")

PYEOF

# Restart service
echo "Restarting deerflow service..."
if [[ $EUID -eq 0 ]]; then
    systemctl restart deerflow
else
    sudo systemctl restart deerflow
fi

# Wait for service
sleep 5

# Verify
echo "Verifying..."
RESULT=$(curl -s -c /tmp/df_verify_cookies.txt -X POST "http://localhost:2026/api/v1/auth/login/local" -H "Content-Type: application/x-www-form-urlencoded" -d "username=wwidjaya@gmail.com&password=P1a0dRxhEZpQWgYFRae2DaCD")
CSRF=$(grep csrf_token /tmp/df_verify_cookies.txt | awk '{print $NF}')
MODELS=$(curl -s -b /tmp/df_verify_cookies.txt -H "X-CSRF-Token: $CSRF" "http://localhost:2026/api/models")

echo "$MODELS" | python3 -c "
import json, sys
data = json.load(sys.stdin)
model_names = [m['name'] for m in data.get('models', [])]
print(f'Models: {model_names}')
if '$NAME' in model_names:
    print(f'SUCCESS: Model \"$NAME\" is configured and is the default (first: {model_names[0] == \"$NAME\"})')
else:
    print(f'ERROR: Model \"$NAME\" not found in API response')
    sys.exit(1)
"

rm -f /tmp/df_verify_cookies.txt
