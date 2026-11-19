---
name: manage-rauthy
description: Manage Rauthy IAM configuration, service lifecycle, themes, and login screen customization for the avrig-ai platform (https://iam.avrig.ai on WSL instance avrig-ai). Use when asked to inspect or update Rauthy config, modify the IAM login screen templates/styles, update the language selector, reload Nginx, or manage rauthy.service.
---

# manage-rauthy

Manages the Rauthy IAM service (OIDC / OAuth 2.1 Identity Provider) and its custom login theme running on WSL instance `avrig-ai` (`https://iam.avrig.ai`).

## Topology & Paths

| Item | Value / Location | Description |
|---|---|---|
| **Domain** | `https://iam.avrig.ai/` | Public IAM endpoint |
| **WSL Instance** | `avrig-ai` | Host Linux distribution |
| **Systemd Unit** | `rauthy.service` | Unit running `/usr/local/bin/rauthy serve -c /etc/rauthy/rauthy.toml` |
| **Config File** | `/etc/rauthy/rauthy.toml` | Core Rauthy server and OIDC configuration |
| **Local Upstream** | `https://127.0.0.1:8443` | TLS listener fronted by local Nginx reverse proxy |
| **Custom Theme Directory** | `/var/www/iam-custom/` | Static theme assets served by Nginx (`avrig-rauthy-theme.css`, logos) |
| **Nginx Site Config** | `/etc/nginx/sites-available/iam.avrig.ai.conf` | Ingress config with sub_filter stylesheet injection and cache-busting |
| **Repository Theme Source** | `apps/web/public/avrig-rauthy-theme.css` | Source stylesheet in `avrig-ai` repository |

## Invocation (PowerShell Wrapper)

```powershell
pwsh $env:OPENCODE_CONFIG_DIR/shared/skills/manage-rauthy/manage-rauthy.ps1 <Action> [Parameters]
```

### Supported Actions

| Action | Description |
|---|---|
| `status` | Checks `rauthy.service` unit status, Nginx status, and `https://127.0.0.1:8443/auth/v1/` endpoint health |
| `logs` | Tails the last 50 lines of `journalctl -u rauthy.service` |
| `config` | Displays `/etc/rauthy/rauthy.toml` configuration |
| `test` | Validates Nginx configuration syntax (`sudo nginx -t`) |
| `reload-nginx` | Tests Nginx config and triggers zero-downtime reload (`systemctl reload nginx`) |
| `restart` | Restarts the background `rauthy.service` daemon |
| `update-theme` | Deploys CSS to `/var/www/iam-custom/avrig-rauthy-theme.css`, updates the cache-bust version in Nginx, and reloads Nginx |

### Examples

```powershell
# Check IAM health and service status
pwsh $env:OPENCODE_CONFIG_DIR/shared/skills/manage-rauthy/manage-rauthy.ps1 status

# Deploy updated theme styling from repo
pwsh $env:OPENCODE_CONFIG_DIR/shared/skills/manage-rauthy/manage-rauthy.ps1 update-theme

# Deploy custom CSS file
pwsh $env:OPENCODE_CONFIG_DIR/shared/skills/manage-rauthy/manage-rauthy.ps1 update-theme -CssPath "D:\custom\theme.css"

# Restart Rauthy daemon
pwsh $env:OPENCODE_CONFIG_DIR/shared/skills/manage-rauthy/manage-rauthy.ps1 restart
```

## Manual Commands (via WSL)

```bash
# Service status & logs
wsl -d avrig-ai -- systemctl status rauthy.service --no-pager
wsl -d avrig-ai -- journalctl -u rauthy.service -n 50 --no-pager

# Direct endpoint check
wsl -d avrig-ai -- curl -k -s https://127.0.0.1:8443/auth/v1/ | head -n 20

# Test & reload Nginx
wsl -d avrig-ai -- sudo nginx -t
wsl -d avrig-ai -- sudo systemctl reload nginx
```
