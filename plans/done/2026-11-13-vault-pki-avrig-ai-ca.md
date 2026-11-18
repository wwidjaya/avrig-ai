---
title: "Plan: Vault PKI Certificate Authority for avrig.ai"
type: canonical
status: completed
source-of-truth: true
domain: engineering
subdomain: infrastructure
category: installation-plan
topic: vault-pki-avrig-ai
created: 2026-11-13
updated: 2026-11-13
author: avrig-ai
tags:
  - plan
  - infrastructure
  - vault
  - pki
  - certificate-authority
  - avrig-ai
  - wsl
---

# Plan: Vault PKI Certificate Authority for avrig.ai

**Status:** Active, approved for development use  
**Project:** AGENTIC / avrig-ai  
**Target:** Ubuntu 24.04 WSL distribution `avrig-ai`, Windows Current User certificate store  
**Scope:** Configure Vault PKI with an offline root and Vault-held intermediate for the internal `avrig.ai` domain. Serve Vault through its Vault Agent Proxy at `https://vault.avrig.ai:8100`, restrict direct backend access to loopback, install only the public root certificate into the Windows Current User trusted root store, and maintain tested recovery and rollback procedures.

## 1. Approved boundaries

- Access Vault through the Vault Agent Proxy only. The Vault server API on port 8200 is a loopback-only backend and is not a client endpoint.
- The proxy endpoint is `https://vault.avrig.ai:8100`, resolved by the existing Samba AD DNS record to the current WSL IPv4 address.
- No public DNS, Windows DNS client, Windows hosts file, LAN firewall, or public network changes are in scope.
- The root CA private key must remain outside Vault and outside version-controlled paths. Only its public certificate is installed in Windows. Vault holds the intermediate CA key and issues leaf certificates.
- Windows trust is limited to the operator's Current User `Root` store. Do not install the CA in the Local Machine store.
- Do not display, copy into notes, or commit recovery tokens, passwords, unseal keys, CA private keys, or issued private keys.

## 2. Preflight state observed

- WSL distro `avrig-ai` is running Ubuntu 24.04.5 LTS.
- Vault 2.2.2, `vault.service`, `vault-proxy.service`, and `samba-ad-dc.service` are active. Vault is initialized and unsealed with Raft storage.
- Windows DNS resolves `vault.avrig.ai` to `172.26.4.57`; WSL system resolution and Samba DNS return the same address. Windows TCP connectivity to proxy port 8100 succeeds.
- Vault server listens on TCP 8200 and proxy on TCP 8100 on all interfaces. Both currently use HTTP. Change only after preparing rollback and validating a candidate TLS endpoint.
- The proxy is configured with AppRole auto-auth references under `/etc/vault.d/proxy-auth/` and an API proxy listener at `/etc/vault.d/vault-proxy.hcl`. Mount inventory requests without an authorized token return 403. Do not use the backend endpoint for client or operator API access.
- The recovery file is not readable by the regular WSL account but is readable by root. Use it only through a protected non-echoing process and never print its contents.

## 3. Planned component topology

| Component | Endpoint or port | Configuration and persistent data | Exposure |
|---|---|---|---|
| Vault server | `127.0.0.1:8200` HTTP backend | `/etc/vault.d/vault.hcl`; Raft data `/var/lib/vault/raft` | Loopback only, proxy upstream |
| Vault Agent Proxy | `https://vault.avrig.ai:8100` | `/etc/vault.d/vault-proxy.hcl`; systemd unit `/etc/systemd/system/vault-proxy.service`; proxy token at `/var/lib/vault-proxy/token` | TLS on WSL address, certificate SAN `vault.avrig.ai` |
| Samba AD DNS | DNS 53 TCP/UDP | Existing Samba configuration and directory state | Existing internal development domain only |
| Vault PKI intermediate | Dedicated PKI mount, final path selected after authenticated mount inventory | Vault Raft storage | Issuance via proxy only |
| Offline root CA | No network listener | Encrypted private-key recovery artifact outside the repository; public certificate exported separately | Signing use only, private key never imported into Vault |
| Windows CA trust | Not applicable | Current User `Cert:\CurrentUser\Root` | Trust only in the operator's Windows profile |

## 4. Execution and safety sequence

1. Capture protected backups of Vault server configuration, proxy configuration, service-unit overrides, Samba DNS record details, and a Vault Raft snapshot. Record file metadata and verify snapshot integrity without exposing secrets.
2. Confirm recovery access and document commands to restore prior configuration, prior proxy behavior, and Vault from its snapshot. Preserve the existing working access path until the HTTPS proxy endpoint is verified.
3. Obtain an authenticated Vault mount inventory through the proxy using protected recovery access. Preserve existing mounts and choose a unique PKI path. Do not recreate or overwrite an existing CA.
4. Prepare an offline root CA and encrypted recovery artifacts outside the repository with restrictive Windows ACLs. Verify recovery material is readable only by the operator and root. Keep temporary unencrypted key material only in protected transient storage and remove it after signing.
5. Configure the dedicated Vault PKI intermediate, sign its CSR with the offline root, configure the issuing role to allow only `avrig.ai` names and subdomains as explicitly approved, set bounded leaf TTLs, and configure issuer and CRL URLs reachable at the proxy endpoint.
6. Issue a short-lived TLS certificate for `vault.avrig.ai` from the intermediate and configure the Vault Agent Proxy TLS listener. Configure its upstream to the loopback-only Vault backend. Restrict Vault server listener to `127.0.0.1:8200` only after proxy TLS and rollback are ready.
7. Verify proxy health, authenticated API operations, certificate hostname and chain, DNS resolution, Windows TCP/TLS connectivity, and that direct backend access from Windows is unavailable.
8. Install the public root CA certificate into the Windows Current User `Root` store. Record the thumbprint and exact removal procedure. Verify Windows chain trust and HTTPS hostname validation.
9. Verify recovery by restoring configuration from backups in a controlled validation, confirm Raft snapshot integrity and the offline CA-key recovery process. Do not perform a destructive restore over live data.
10. Update `infra/Infrastructure.md` with verified versions, paths, service units, proxy URL, ports, CA trust location, secret path references only, and operational checks. Mark this plan completed and move it to `plans/done/` only after all checks pass.

## 5. Recovery and rollback

- Keep timestamped backups of every changed configuration file with restrictive permissions. Before each service restart, validate configuration syntax and preserve the existing file for immediate rollback.
- Keep a verified Vault Raft snapshot outside the repository, protected by operator-only Windows ACLs. Confirm the snapshot can be listed and validated before relying on it.
- If TLS proxy validation fails, restore the proxy configuration and service unit, restart the proxy, and verify its prior local HTTP health path. Keep the Vault backend available on loopback for recovery only. Do not re-expose port 8200 externally.
- If restricting the Vault server listener interrupts service, restore the backed-up listener configuration and service unit, restart Vault, and validate Vault health through the proxy. Keep the old proxy path available until HTTPS is proven.
- Protect the encrypted offline root-key artifact and its decryption material separately. Maintain an encrypted backup on a separate operator-controlled medium. Never store the CA private key or passphrase in Git, Vault documentation, shell history, or tool output.
- For Windows trust rollback, remove only the installed root certificate matching the recorded thumbprint from `Cert:\CurrentUser\Root`; do not remove unrelated certificates.
- For DNS rollback, preserve the pre-change Samba record state and revert only the specific `vault.avrig.ai` record if this plan adds or changes one. Do not modify general WSL or Windows DNS settings.

## 6. Verification checklist

- [ ] Existing Vault and Samba services remain healthy; no unrelated services or DNS records changed.
- [ ] Vault backend listens only on `127.0.0.1:8200` and is not used as the service endpoint.
- [ ] Vault Agent Proxy serves `https://vault.avrig.ai:8100` with a certificate containing the correct SAN and complete intermediate chain.
- [ ] Windows resolves `vault.avrig.ai`, connects to proxy port 8100, and validates TLS after Current User root installation.
- [ ] Direct Windows access to Vault backend port 8200 fails.
- [ ] Vault PKI mount and role are scoped to `avrig.ai`, with bounded TTL and no unauthorized domains.
- [ ] A test leaf certificate is issued through the proxy and validates to the installed root CA.
- [ ] Root private key remains outside Vault and repository; only the public root certificate is installed in Windows.
- [ ] Recovery file, Raft snapshot, configuration backups, offline root key, and passphrase have restrictive access and verified recovery steps.
- [ ] Infrastructure baseline is updated with actual verified state and no secret values.

## 7. Official reference

- HashiCorp Vault PKI documentation: https://developer.hashicorp.com/vault/docs/secrets/pki
- HashiCorp Vault intermediate CA quick start: https://developer.hashicorp.com/vault/docs/secrets/pki/quick-start-intermediate-ca
