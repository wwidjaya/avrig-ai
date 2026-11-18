---
name: manage-nginx
description: Manage the nginx reverse proxy on WSL `research` — list/show/expose sites, test config, reload/restart/start/stop, tail logs, and create a new HTTPS reverse-proxy vhost from a template. Use when asked to add/enable/disable a nginx site, create a new nginx vhost, reload/restart/status nginx, test nginx config, or check nginx logs.
---

# manage-nginx

Manages the nginx reverse proxy that fronts the `*.wirianto.ai` services. nginx runs inside the WSL instance `research` (service `nginx.service`, nginx 1.24.0).

## Access

All commands run inside the WSL instance `research`:

- **Windows:** `wsl -d research -- bash -lc "<command>"`
- **WSL/Linux:** `bash -lc "<command>"` inside the `research` instance

Passwordless sudo is configured — `sudo systemctl ...`, `sudo nginx -t`, etc. work without a password prompt.

## Paths

| Path | Purpose |
|---|---|
| `/etc/nginx/sites-available/<site>` | site configs |
| `/etc/nginx/sites-enabled/<site>` | symlinks to enabled sites |
| `/etc/nginx/ssl/<fqdn>.*` | TLS cert/key/chain |
| `/var/log/nginx/error.log` | error log |
| `/var/log/nginx/access.log` | access log |
| `/etc/nginx/snippets/`, `/etc/nginx/proxy_params` | shared include fragments |

nginx loads `conf.d/*.conf` then `sites-enabled/*`.

## Primary invocation (wrapper)

```
pwsh $env:OPENCODE_CONFIG_DIR/shared/skills/manage-nginx/manage-nginx.ps1 <cmd> [args]
```

Commands:

| Command | Action |
|---|---|
| `status` | nginx service status + listening ports |
| `test` | `nginx -t` config check |
| `list` | enabled sites (available by default; `list -All` shows all available) |
| `show <site>` | print a site config |
| `enable <site>` | symlink `sites-available/<site>` → `sites-enabled/`, then `nginx -t` and reload |
| `disable <site>` | remove symlink, then `nginx -t` and reload |
| `reload` | `nginx -t && systemctl reload nginx` |
| `restart` | `nginx -t && systemctl restart nginx` |
| `start` / `stop` | `systemctl start|stop nginx` |
| `logs [site]` | tail error.log (optionally filtered to a site/`server_name`) |
| `create <fqdn> <upstream>` | create an HTTPS vhost (see below), `nginx -t`, symlink, reload |

Examples:

```
pwsh $env:OPENCODE_CONFIG_DIR/shared/skills/manage-nginx/manage-nginx.ps1 list
pwsh $env:OPENCODE_CONFIG_DIR/shared/skills/manage-nginx/manage-nginx.ps1 show vector.wirianto.ai
pwsh $env:OPENCODE_CONFIG_DIR/shared/skills/manage-nginx/manage-nginx.ps1 test
pwsh $env:OPENCODE_CONFIG_DIR/shared/skills/manage-nginx/manage-nginx.ps1 reload
pwsh $env:OPENCODE_CONFIG_DIR/shared/skills/manage-nginx/manage-nginx.ps1 create pa.wirianto.ai 172.26.0.1:42617
```

## Manual commands

### status / test

```bash
wsl -d research -- bash -lc "systemctl status nginx --no-pager -l | head -12"
wsl -d research -- bash -lc "sudo nginx -t"
wsl -d research -- bash -lc "sudo ss -tlnp | grep -E ':80|:443'"
```

### list sites

```bash
wsl -d research -- bash -lc "ls -1 /etc/nginx/sites-enabled/"
wsl -d research -- bash -lc "grep -l server_name /etc/nginx/sites-available/* | xargs -I{} basename {}"
```

### show / enable / disable

```bash
wsl -d research -- bash -lc "cat /etc/nginx/sites-available/<site>"
wsl -d research -- bash -lc "sudo ln -s /etc/nginx/sites-available/<site> /etc/nginx/sites-enabled/<site> && sudo nginx -t && sudo systemctl reload nginx"
wsl -d research -- bash -lc "sudo rm /etc/nginx/sites-enabled/<site> && sudo systemctl reload nginx"
```

### reload / restart

```bash
wsl -d research -- bash -lc "sudo nginx -t && sudo systemctl reload nginx"
wsl -d research -- bash -lc "sudo nginx -t && sudo systemctl restart nginx"
```

### logs

```bash
wsl -d research -- bash -lc "sudo tail -n 50 /var/log/nginx/error.log"
# site-specific (grep by server_name)
wsl -d research -- bash -lc "sudo tail -n 50 /var/log/nginx/error.log | grep <site>"
```

## Creating a new vhost (`create`)

`create <fqdn> <upstream>` writes a standard reverse-proxy vhost to `/etc/nginx/sites-available/<fqdn>`:

```nginx
server {
    listen 80;
    listen [::]:80;
    server_name <fqdn>;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name <fqdn>;

    ssl_certificate     /etc/nginx/ssl/<fqdn>.crt;
    ssl_certificate_key /etc/nginx/ssl/<fqdn>.key;
    ssl_trusted_certificate /etc/nginx/ssl/wirianto-ca.crt;

    location / {
        proxy_pass http://<upstream>;
        proxy_http_version 1.1;
        include /etc/nginx/proxy_params;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_buffering off;
        proxy_cache off;
    }
}
```

- `<upstream>` is `host:port` (e.g. `127.0.0.1:8200`, `172.26.0.1:42617`) or the name of an `upstream {}` block.
- The `Host` header comes from `include proxy_params` (`Host $http_host`) — do **not** add a second `proxy_set_header Host` in the `location` block. A duplicate `Host:` header makes Go backends (e.g. Ollama) respond `400 Bad Request`.
- The cert files **must already exist** in `/etc/nginx/ssl/` before `create` — otherwise `nginx -t` fails. Mint them first with the `issue-cert` skill (run `wsl -d research -- bash -lc "ls /etc/nginx/ssl/<fqdn>.*"` to confirm).
- After writing, the wrapper runs `nginx -t`; on success it symlinks the site into `sites-enabled/` and reloads.
- If the vhost already exists, the wrapper backs it up to `.bak` before overwriting (it does not touch the enabled symlink or reload unless the config passes `nginx -t`).

## Cross-links

- **`issue-cert`** — mint/renew `*.wirianto.ai` TLS certs into `/etc/nginx/ssl` (do this before `create` or when renewing).
- **`manage-dns`** — add/update the AD DNS `A` record for the hostname (`samba-tool dns`, zone `wirianto.ai`, target `172.26.0.50`).
- **`unblock-vpn`** — OpenVPN leak-protection WFP filters can block port-53 to `172.26.0.50`; if DNS/`Resolve-DnsName`/`samba-tool dns` fails, re-run `D:\Development\kb\scripts\unblock-openvpn\unblock-openvpn.exe install` elevated.

## Gotchas

- Always gate `reload`/`restart` behind `nginx -t` — never reload a broken config.
- `enable`/`create` run `nginx -t` on the new config before symlinking/reloading.
- If a site already exists, never destroy it silently — back it up to `.bak` first.
- Naming: vhost file names = the FQDN (e.g. `vector.wirianto.ai`), symlinks match in `sites-enabled`.
- The `research` site is special-cased (multiple `location` blocks, `upstream gateway`/`upstream frontend` defined in `nginx.conf`); `create` produces a simple single-location vhost — edit manually for complex layouts.
- nginx ssl file ownership is `root:www-data` mode `0640` (set by `issue-cert` install).
