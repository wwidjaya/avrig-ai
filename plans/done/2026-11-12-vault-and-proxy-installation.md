---
title: "Plan: HashiCorp Vault Server and Vault Proxy Installation on WSL (Ubuntu 24.04)"
type: canonical
status: completed
source-of-truth: true
domain: engineering
subdomain: infrastructure
category: installation-plan
topic: vault-and-proxy-wsl-setup
created: 2026-11-12
updated: 2026-11-12
author: avrig-ai
tags:
  - plan
  - infrastructure
  - vault
  - vault-proxy
  - wsl
  - ubuntu
  - systemd
---

# Plan: HashiCorp Vault Server and Vault Proxy Installation on WSL (Ubuntu 24.04)

**Status:** Completed & Verified  
**Project:** AGENTIC / avrig-ai  
**Scope:** Install and configure HashiCorp Vault Server with persistent integrated Raft storage and a companion Vault Agent Proxy service under native systemd on the existing Ubuntu 24.04 WSL instance (`avrig-ai`). The setup provides local secrets management reachable from both WSL and the Windows host, configures a development-only recovery-key file outside the repository, and updates `infra/Infrastructure.md`.

---

## 1. Architectural Strategy & Safety Boundaries

This deployment provisions a production-shaped development baseline for secrets management without running Vault in transient in-memory dev mode:

1. **Persistent Vault Server (`vault.service`):**
   - Installed from HashiCorp's official Ubuntu repository.
   - Uses integrated Raft storage under `/var/lib/vault/raft` on the dedicated WSL virtual disk (`D:\wsl\avrig-ai\ext4.vhdx`).
   - Serves the Vault API on `0.0.0.0:8200` to allow access from both internal WSL services and Windows host tools.
2. **Local Vault Agent Proxy (`vault-proxy.service`):**
   - Runs as a dedicated client-side proxy service on `0.0.0.0:8100`.
   - Proxies incoming API calls to the Vault Server, provides a caching layer, and supports AppRole / token-file based auto-auth for local development clients.
3. **Recovery Material Placement Rule:**
   - Approved dev recovery material (unseal keys and initial root token) must be stored **strictly outside the repository** in `D:\wsl\avrig-ai\secrets\vault-recovery.txt` (WSL path: `/mnt/d/wsl/avrig-ai/secrets/vault-recovery.txt`).
   - Windows file permissions must be restricted to the active operator user account.
   - The key file must never be placed inside `avrig-ai/infra/` or any version-controlled folder.

---

## 2. Target Component Topology

| Component | Service Name | Internal Port | Protocol | Data & Config Paths | Purpose |
|---|---|---|---|---|---|
| **Vault Server** | `vault.service` | `8200` | HTTP / API | Config: `/etc/vault.d/vault.hcl`<br>Data: `/var/lib/vault/raft` | Authoritative secrets engine, KV v2 store, policy engine |
| **Vault Proxy** | `vault-proxy.service` | `8100` | HTTP / API | Config: `/etc/vault.d/vault-proxy.hcl`<br>Run: `/run/vault-proxy` | Local client-facing cache, request proxy, auto-auth runner |
| **Recovery Store** | External File | N/A | Text | `D:\wsl\avrig-ai\secrets\vault-recovery.txt` | Unseal shares and bootstrap root token for dev recovery |

---

## 3. Step-by-Step Implementation Sequence

### Phase 1: Repository Setup & Package Installation
1. Add HashiCorp official GPG keyring to `/usr/share/keyrings/hashicorp-archive-keyring.gpg`.
2. Register the signed HashiCorp APT repository for Ubuntu Noble (`noble`).
3. Update package index and install `vault` package via `apt-get`.
4. Create the dedicated recovery directory on drive D:
   - Create directory `D:\wsl\avrig-ai\secrets` with restricted access permissions.

### Phase 2: Vault Server Configuration (Raft Backend)
1. Prepare directories `/var/lib/vault/raft` and `/var/log/vault` owned by user `vault:vault`.
2. Configure `/etc/vault.d/vault.hcl`:
   - Set `ui = true`.
   - Set `disable_mlock = true` (optimized for WSL memory model).
   - Configure `storage "raft"` with `path = "/var/lib/vault/raft"` and `node_id = "avrig-vault-node-1"`.
   - Configure `listener "tcp"` on `0.0.0.0:8200` with `tls_disable = 1` for local development.
   - Configure `api_addr = "http://127.0.0.1:8200"`.
3. Enable and start `vault.service` under systemd.

### Phase 3: Initialization & External Secret Capture
1. Run `vault operator init -key-shares=1 -key-threshold=1 -format=json`.
2. Save the output JSON securely into `/mnt/d/wsl/avrig-ai/secrets/vault-recovery.txt`.
3. Set strict file permissions (`chmod 600` / Windows ACL restricting read to operator).
4. Unseal Vault using the unseal key from the recovery file.
5. Log in with the initial root token:
   - Enable file audit device to `/var/log/vault/audit.log`.
   - Enable KV v2 secrets engine at path `secret/`.
   - Create project base KV mount `secret/avrig-ai`.

### Phase 4: Vault Proxy Configuration & Service
1. Create a dedicated AppRole or token role for the local proxy.
2. Configure `/etc/vault.d/vault-proxy.hcl`:
   - Set `vault { address = "http://127.0.0.1:8200" }`.
   - Configure `auto_auth` using the local token file or AppRole.
   - Configure `api_proxy { use_auto_auth_token = true }`.
   - Configure `listener "tcp"` on `0.0.0.0:8100` with `tls_disable = 1`.
3. Deploy systemd unit `/etc/systemd/system/vault-proxy.service`.
4. Enable and start `vault-proxy.service`.

### Phase 5: Verification & Diagnostics Checklist
1. **Service Checks:**
   - Confirm `systemctl is-active vault` reports `active`.
   - Confirm `systemctl is-active vault-proxy` reports `active`.
2. **Seal & Health Check:**
   - Run `vault status` against port `8200` (sealed: false).
3. **Proxy Functional Test:**
   - Write a test secret through the Vault Server:
     `vault kv put secret/avrig-ai/test-key value="test-secret"`
   - Read the test secret back through the Vault Proxy port `8100`:
     `curl -s http://127.0.0.1:8100/v1/secret/data/avrig-ai/test-key`
4. **Host Reachability Check:**
   - Run a test request from Windows host PowerShell against `http://localhost:8200/v1/sys/health` and `http://localhost:8100/v1/sys/health`.

### Phase 6: Documentation & Plan Completion
1. Update `infra/Infrastructure.md`:
   - Add Vault Server and Vault Proxy to the software inventory table.
   - Document ports `8200` and `8100` in the network ports table.
   - Document configuration file paths and persistent storage locations.
   - Document the path of the external recovery file `D:\wsl\avrig-ai\secrets\vault-recovery.txt` without embedding secrets.
   - Document unseal, restart, and operational CLI commands.
2. Update `.env.development` with `VAULT_ADDR="http://127.0.0.1:8200"` and `VAULT_PROXY_ADDR="http://127.0.0.1:8100"`.
3. Move this plan to `plans/done/` and update `_index.md`.
