---
name: manage-vault
description: Manage HashiCorp Vault server and Vault Agent Proxy on the avrig-ai platform (WSL instance avrig-ai). Issue TLS certificates via PKI (pki_avrig_ai mount, role avrig-ai-dot-ai), inspect Vault status, manage Transit secrets, and configure proxy auto-auth.
---

# manage-vault

Manages HashiCorp Vault Server, Vault Agent Proxy, and the internal PKI Engine for the `avrig.ai` domain on the WSL instance `avrig-ai`.

## Topology and Access

| Component | Endpoint | Binding / Transport | Notes |
| :--- | :--- | :--- | :--- |
| **Vault Server** | `http://127.0.0.1:8200` | Loopback only | Raft storage backend (`/var/lib/vault/raft`), service `vault.service` |
| **Vault Agent Proxy** | `https://vault.avrig.ai:8100` | `0.0.0.0:8100` (TLS) | Client-facing TLS proxy with AppRole auto-auth, service `vault-proxy.service` |
| **Proxy Auto-Auth Token** | `/var/lib/vault-proxy/token` | Local file | Service token with `avrig-proxy` and `default` policies |
| **Recovery Material** | `D:\wsl\avrig-ai\secrets\vault-recovery.txt` | File (`0600`) | Contains bootstrap `root_token` and unseal shares |
| **Root CA Certificate** | `/etc/nginx/ssl/avrig-root-ca.crt` | Public Certificate | Offline root CA public cert (`CN = avrig.ai Root CA`) |
| **PKI Engine** | Mount: `pki_avrig_ai/` | Role: `avrig-ai-dot-ai` | Intermediate CA signed by offline Root CA (max TTL: 2160h / 90 days) |

## Core Commands

### 1. Check Service & Health Status

```bash
# Check service units
wsl -d avrig-ai -- systemctl status vault --no-pager
wsl -d avrig-ai -- systemctl status vault-proxy --no-pager

# Check unsealed state via loopback
wsl -d avrig-ai -- curl -s http://127.0.0.1:8200/v1/sys/health | jq .

# Check health via TLS proxy (port-free via Nginx on port 443)
wsl -d avrig-ai -- curl --cacert /etc/nginx/ssl/avrig-root-ca.crt -s https://vault.avrig.ai/v1/sys/health | jq .

# Check health via direct Vault Proxy listener (port 8100)
wsl -d avrig-ai -- curl --cacert /etc/nginx/ssl/avrig-root-ca.crt -s https://vault.avrig.ai:8100/v1/sys/health | jq .
```

### 2. Issue TLS Certificate for avrig.ai Domain

The PKI role `avrig-ai-dot-ai` under `pki_avrig_ai/` issues leaf certificates for `*.avrig.ai`.

#### Automatic issuance and installation via Python (recommended):

```python
import json, subprocess

# Load bootstrap token
with open("/mnt/d/wsl/avrig-ai/secrets/vault-recovery.txt") as f:
    token = json.load(f)["root_token"].strip()

# Target FQDN (e.g., api.avrig.ai)
fqdn = "api.avrig.ai"
payload = json.dumps({
    "common_name": fqdn,
    "alt_names": "localhost",
    "ip_sans": "127.0.0.1,172.26.4.57",
    "ttl": "2160h"
})

res = subprocess.run([
    "curl", "-s", "-H", f"X-Vault-Token: {token}",
    "-X", "POST", "-d", payload,
    "http://127.0.0.1:8200/v1/pki_avrig_ai/issue/avrig-ai-dot-ai"
], capture_output=True, text=True)

data = json.loads(res.stdout)["data"]
cert = data["certificate"]
chain = "\n".join(data.get("ca_chain", []))
key = data["private_key"]

fullchain = f"{cert}\n{chain}\n"
with open(f"/etc/nginx/ssl/{fqdn}.crt", "w") as f:
    f.write(fullchain)
with open(f"/etc/nginx/ssl/{fqdn}.key", "w") as f:
    f.write(key.strip() + "\n")
```

#### Set proper file permissions for Nginx:

```bash
sudo chmod 0644 /etc/nginx/ssl/<fqdn>.crt
sudo chmod 0600 /etc/nginx/ssl/<fqdn>.key
sudo chown root:root /etc/nginx/ssl/<fqdn>.*
```

### 3. Verify Issued Certificate

```bash
# Verify subject, issuer, and SAN extensions
openssl x509 -in /etc/nginx/ssl/<fqdn>.crt -noout -subject -issuer -ext subjectAltName

# Verify certificate against the platform root CA
openssl verify -CAfile /etc/nginx/ssl/avrig-root-ca.crt /etc/nginx/ssl/<fqdn>.crt
```

### 4. Vault Proxy Auto-Auth Details

The Vault Agent Proxy automatically renews its token using AppRole credentials:
- **Role ID**: `/etc/vault.d/proxy-auth/role_id`
- **Secret ID**: `/etc/vault.d/proxy-auth/secret_id`
- **Token Sink**: `/var/lib/vault-proxy/token`
- **Config**: `/etc/vault.d/vault-proxy.hcl`

To inspect the proxy token:
```bash
wsl -d avrig-ai -u root -- bash -c '
TOKEN=$(cat /var/lib/vault-proxy/token)
curl -s -H "X-Vault-Token: $TOKEN" http://127.0.0.1:8200/v1/auth/token/lookup-self | jq .data
'
```

### 5. Transit Decryption for Applications

Applications such as `avrig` decrypt ciphertext (`vault:v1:...`) using Vault Transit engine:
- **Mount**: `transit/`
- **Key**: `avrig-config`
- **Endpoint**: `POST /v1/transit/decrypt/avrig-config`
- **Payload**: `{"ciphertext": "vault:v1:..."}`
- **Response**: Base64 encoded plaintext in `.data.plaintext`
