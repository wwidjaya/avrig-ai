---
name: issue-cert
description: Mint TLS leaf certificates from the HashiCorp Vault PKI (WSL `research`, mount `pki/`, role `wirianto-dot-ai`) for `*.wirianto.ai`, with optional auto-install into `/etc/nginx/ssl` and nginx reload. Use when asked to generate, provision, issue, renew, or create an SSL/HTTPS/TLS certificate for a wirianto.ai subdomain (e.g. `foo.wirianto.ai`).
---

# issue-cert

Mints leaf certificates signed by the **`wirianto.ai Root CA 2026`** (held in HashiCorp Vault's PKI engine), then optionally installs them for nginx.

## Access

Vault runs inside the WSL instance `research` (systemd service `vault.service`):

- **Windows:** `wsl -d research -- bash -lc "<command>"`
- **Vault binary:** `/opt/vault/vault`
- **Vault Proxy API:** `http://127.0.0.1:8202` (auto-auth via AppRole `agentic-api`; no token needed)
- **PKI mount:** `pki/` — role `wirianto-dot-ai` (allows `wirianto.ai` subdomains + wildcards, `allow_ip_sans`, default TTL 90d, max 7776000s)

Export env for manual use (no token; the proxy auto-authenticates):

```bash
export VAULT_ADDR=http://127.0.0.1:8202
```

## Primary invocation (wrapper)

```
pwsh $env:OPENCODE_CONFIG_DIR/shared/skills/issue-cert/issue-cert.ps1 <fqdn> [-Ttl <ttl>] [-Out <dir>] [-InstallNginx] [-Reload]
```

- `<fqdn>` — required, e.g. `pa.wirianto.ai` (must end in `.wirianto.ai`; warns otherwise)
- `-Ttl` — optional, default `2160h` (90 days; matches existing certs)
- `-Out <dir>` — where to write `.crt` / `.key` / `.chain.crt` on Windows; default = current directory
- `-InstallNginx` — also copy into `/etc/nginx/ssl/<fqdn>.*` inside `research` with `root:www-data 0640`
- `-Reload` — run `nginx -t && systemctl reload nginx` after install (implies `-InstallNginx`)

The wrapper runs the `vault write` inside WSL, parses the JSON, saves the three files on the Windows side, and (optionally) installs them for nginx.

## Manual commands

### Issue a certificate (JSON to a file)

```bash
wsl -d research -- bash -lc "export VAULT_ADDR=http://127.0.0.1:8202 && /opt/vault/vault write -format=json pki/issue/wirianto-dot-ai common_name=pa.wirianto.ai ttl=2160h > /tmp/pa-cert.json"
```

Extract fields (`certificate`, `private_key`, `ca_chain[0]` = root CA) and write:

- `pa.wirianto.ai.crt`        = certificate
- `pa.wirianto.ai.key`        = private_key
- `pa.wirianto.ai.chain.crt`  = certificate + "\n" + ca_chain[0]

### Inspect the PKI role

```bash
wsl -d research -- bash -lc "export VAULT_ADDR=http://127.0.0.1:8202 && /opt/vault/vault list pki/roles && /opt/vault/vault read -format=json pki/roles/wirianto-dot-ai"
```

### Verify the issued cert

```bash
# Against the nginx-installed root CA
openssl verify -CAfile /etc/nginx/ssl/wirianto-ca.crt pa.wirianto.ai.crt
openssl x509 -in pa.wirianto.ai.crt -noout -subject -issuer -enddate -ext subjectAltName
```

## Install for nginx (manual equivalent of `-InstallNginx`)

```bash
wsl -d research -- bash -lc "sudo install -o root -g www-data -m 0640 /mnt/c/<out>/pa.wirianto.ai.crt /etc/nginx/ssl/ && sudo install -o root -g www-data -m 0640 /mnt/c/<out>/pa.wirianto.ai.key /etc/nginx/ssl/"
```

Reference config pattern (`/etc/nginx/sites-available/<fqdn>`):

```nginx
server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name pa.wirianto.ai;

    ssl_certificate     /etc/nginx/ssl/pa.wirianto.ai.crt;
    ssl_certificate_key /etc/nginx/ssl/pa.wirianto.ai.key;
    ssl_trusted_certificate /etc/nginx/ssl/wirianto-ca.crt;

    location / {
        proxy_pass http://127.0.0.1:PORT;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

Then symlink into `sites-enabled` and `sudo nginx -t && sudo systemctl reload nginx`.

## DNS

This skill is **cert-only**. Adding/updating the DNS A record for the new hostname in the AD domain is a separate step (`samba-tool dns add` on WSL `ad`, or the `write-ldap` skill flow) — do it before or alongside issuing if the hostname must resolve.

## Gotchas

- Token is a Vault **root** token — never print it, never write it into a repo, never log it.
- The vault `write` response contains the private key; prefer writing straight to the target files and cleaning up intermediate JSON.
- Existing services use TTL `2160h` (90d) and SAN = CN. Role `allow_wildcard_certificates=true` so `*.wirianto.ai` works if needed (pass `common_name=*.wirianto.ai`).
- nginx ssl file ownership is `root:www-data` with mode `0640` — do not use `0644` on the `.key`.
- The AD DNS (`172.26.0.50`) may be blocked by OpenVPN leak-protection WFP filters; if `samba-tool dns`/DNS lookups fail, re-run `D:\Development\kb\scripts\unblock-openvpn\unblock-openvpn.exe install` (elevated).
