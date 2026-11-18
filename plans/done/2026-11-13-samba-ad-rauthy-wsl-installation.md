---
title: "Plan: Samba AD DNS and Rauthy IAM Installation on WSL"
type: canonical
status: completed
source-of-truth: true
domain: engineering
subdomain: infrastructure
category: installation-plan
topic: samba-ad-rauthy-wsl
created: 2026-11-13
updated: 2026-11-13
author: avrig-ai
tags:
  - plan
  - infrastructure
  - samba
  - active-directory
  - dns
  - rauthy
  - iam
  - wsl
---

# Plan: Samba AD DNS and Rauthy IAM Installation on WSL

**Status:** Active, approved for development-only deployment  
**Project:** AGENTIC / avrig-ai  
**Target:** Ubuntu 24.04 WSL distribution `avrig-ai`  
**Scope:** Provision a new Samba Active Directory domain `AVRIG.AI` with Samba's integrated DNS backend, then deploy Rauthy IAM using its official container image and persistent local data. Services are for this development environment only. Windows NRPT split-DNS routing for only `avrig.ai` is approved. No Windows interface DNS changes, LAN DNS changes, firewall changes, public DNS changes, Google OAuth credentials, or production configuration are in scope.

---

## 1. Approved Decisions and Assumptions

- Forest/domain DNS name: `avrig.ai` exactly; Kerberos realm: `AVRIG.AI`; NetBIOS domain: `AVRIG`.
- Samba AD integrated DNS backend: `SAMBA_INTERNAL`; no separate BIND DNS server.
- The existing WSL distro `avrig-ai` is the only target. Do not join another domain or modify other WSL distributions. Windows host queries for `avrig.ai` should use Samba integrated DNS.
- DNS is development-only. Windows NRPT split-DNS for only `avrig.ai` is explicitly approved. Do not change Windows interface DNS settings, LAN router settings, public DNS records, or Windows firewall rules.
- The public `avrig.ai` zone may overlap with this internal authoritative AD zone. Public DNS lookups could not be verified from the current host during preflight. Existing WSL external DNS forwarding will be preserved; public records beneath `avrig.ai` may require explicit split-DNS records if they are later needed inside the WSL distro.
- Rauthy uses its documented embedded Hiqlite storage, not the existing application PostgreSQL instance.
- Google upstream OAuth is not configured in this installation because the Google OAuth client credentials and exact callback registration are not yet provisioned.
- Rauthy is bound to loopback only and uses local development TLS. This is not a production or LAN deployment.

---

## 2. Preflight State and Compatibility

Observed on Ubuntu 24.04.5 LTS (`noble`):

- PID 1 is systemd.
- Samba packages, Samba configuration, Samba private database paths, Rauthy, and container runtimes were not present at inspection time.
- `systemd-resolved` is active and owns loopback DNS stub listeners on `127.0.0.53:53` and `127.0.0.54:53`.
- `/etc/resolv.conf` is WSL-generated (`/mnt/wsl/resolv.conf`) and points to the WSL host resolver `172.26.0.1`.
- Existing Vault and Vault Agent Proxy services use ports 8200 and 8100. They must remain healthy.
- Ubuntu Noble repository candidates observed: Samba AD DC `4.19.5+dfsg-4ubuntu9.8` and DNS diagnostic tools from Ubuntu repositories. Packages have since been installed; package setup started standalone Samba units that must be stopped before provisioning.
- The Rauthy official guide supports container deployment and documents image tag `0.37.2`; use a pinned image tag, not `latest`.

Before changing resolver or service configuration, re-check these facts and the currently resolved WSL interface address. Do not assume cached package or network state is unchanged.

---

## 3. Intended Service Layout

| Component | Service | Listener/Ports | Persistent/configuration paths | Notes |
|---|---|---|---|---|
| Samba AD DC | `samba-ad-dc.service` | AD ports including DNS 53, Kerberos 88, RPC 135, LDAP 389, SMB 445, and 464, bound only to loopback and WSL `eth0` | `/etc/samba/smb.conf`; `/var/lib/samba`; `/var/cache/samba`; `/var/log/samba` | Integrated DNS; Windows host access through WSL virtual networking and zone-scoped NRPT. No LAN/router DNS changes. |
| Rauthy IAM | `rauthy.service` (systemd-managed Podman container) | HTTPS 8443, published only on `127.0.0.1:8443` | `/etc/rauthy/config.toml`; `/var/lib/rauthy/data`; `/var/lib/rauthy/tls` if needed | Pin `ghcr.io/sebadob/rauthy:0.37.2`; use locally scoped development configuration and persistent Hiqlite data. |
| Podman | Podman runtime | No host listener required | Container image cache under system storage; Rauthy bind mounts above | Installed from Ubuntu Noble repository if preflight still confirms absent. |

The systemd-resolved stub and WSL-generated resolver must remain unchanged. Samba AD ports, including integrated DNS on TCP/UDP 53, must bind only to loopback and the current WSL `eth0` address, not all interfaces. Use Windows Name Resolution Policy Table (NRPT) to route only `.avrig.ai` queries to the current WSL interface address. Do not change Windows interface DNS settings, global DNS, LAN/router DNS, or firewall rules. Since the WSL address can change after restart, document and verify how the policy target is refreshed; do not silently leave stale policy.

---

## 4. Security and Secret Handling

- Generate a unique Samba Administrator password and Rauthy initial admin credential. Never print either credential in tool output or documentation.
- Store administrative recovery credentials only outside the repository in the WSL-native root-owned directory `/root/avrig-ai-secrets/`, with directory mode 700 and individual files mode 600. The pre-existing D: secrets directory has inherited broad Windows ACLs, so do not put new credentials there unless those ACLs are separately secured and verified.
- Store Google OAuth client secrets only when the operator supplies them, in the approved secret store. Do not put them in Rauthy config in plaintext, shell history, logs, `.env` files, or this plan.
- Use Rauthy's production-style generated configuration, not the documented `LOCAL_TEST=true` demo configuration, which the vendor identifies as unsafe and localhost-only.
- Keep Rauthy bound to `127.0.0.1`. Do not publish it to all interfaces or use public reverse proxy exposure.
- No secrets, generated credentials, or recovery keys belong in Git or Vault documentation.

---

## 5. Execution Phases

### Phase A: Re-check and Back Up Configuration
1. Reconfirm distro, Ubuntu version, systemd state, host/interface addresses, package versions, listeners, `/etc/wsl.conf`, `/etc/resolv.conf`, `/etc/hosts`, and service status.
2. Create a root-only timestamped backup of resolver, host, and generated Samba package configuration before altering any of it. Record a rollback command in the operator session without recording secret data.
3. Public DNS lookup for `avrig.ai` was unavailable from the current host. Do not claim public zone compatibility is verified. Keep the internal AD listener loopback-only and preserve external WSL resolution.

### Phase B: Install and Provision Samba AD with Integrated DNS
1. Samba AD DC and diagnostic packages were installed from signed Ubuntu Noble repositories; no BIND server was installed.
2. Stop and disable standalone `smbd`, `nmbd`, and `winbind` units started by package setup. Provision the forest with realm `AVRIG.AI`, NetBIOS domain `AVRIG`, `SAMBA_INTERNAL` DNS, and Samba bound only to `lo`. Use a non-echoed password prompt and a securely generated external credential file, never a password on the command line.
3. Enable `samba-ad-dc` only after successful provisioning. Keep systemd-resolved and the WSL-generated resolver intact; use explicit `dig @127.0.0.1` for dev DNS queries.
4. Verify service health, Kerberos, LDAP, SYSVOL/NETLOGON shares, and DNS SRV/A records using `samba-tool`, `kinit`, `smbclient`, and `dig` without outputting credentials.
### Phase C: Install Podman and Deploy Rauthy
1. Install Podman from Ubuntu's Noble repository if still absent. Do not install an unneeded external Docker daemon.
2. Create `/etc/rauthy` and `/var/lib/rauthy/data` with least-privilege ownership and modes suitable for the image's documented UID `10001`.
3. Generate and review a Rauthy config using the pinned official image `ghcr.io/sebadob/rauthy:0.37.2`. Configure stable local issuer URL and local TLS appropriate to localhost development. Do not set `LOCAL_TEST=true`.
4. Protect configuration and initial admin credentials. Ensure first-start generated credentials are captured securely without exposing container logs or secret values.
5. Create a systemd-managed Podman container service with restart behavior and a loopback-only published port `127.0.0.1:8443:8443`.
6. Start the service and verify systemd health, HTTPS health endpoint, OIDC discovery document, issuer consistency, and persistence after a controlled service restart.

### Phase D: Documentation and Completion
1. Update `infra/Infrastructure.md` with actual component versions, service units, DNS and Rauthy ports/bindings, configuration/data paths, secret-file paths only, and verified operational commands.
2. Update `_index.md` to link the active plan.
3. Mark the plan completed and move to `plans/done/` only after all declared checks pass. Otherwise retain it as active and record blockers/partial status.

---

## 6. System Impact, Ports, and Recovery

- Samba AD introduces persistent directory state and binds multiple AD ports. Port 53 currently has systemd-resolved loopback listeners, so the DNS bind interaction is a mandatory preflight gate.
- WSL and Windows default resolvers remain unchanged. Samba DNS can be queried locally at `127.0.0.1`; applications that need AD DNS must explicitly use that resolver. Public resolution for names inside the authoritative `avrig.ai` zone may require split-DNS records.
- Windows NRPT split-DNS is authorized only for `avrig.ai`, targeting the current WSL `eth0` address. Preserve and verify all pre-existing NRPT entries, including `.wirianto.ai` to `172.26.0.50`. Do not alter interface DNS settings, firewall rules, or LAN DNS. Windows AD client/domain join is outside this DNS-routing task.
- WSL address observed before this change: `172.26.4.57/20`. NRPT can become stale if WSL receives a new address. Record the exact installed rule and rollback procedure, verify Windows DNS queries after the change, and re-check address consistency after a WSL restart.
- Windows NRPT rule `.avrig.ai` -> `172.26.4.57` is installed and verified. DNS port 53 WFP filter for `172.26.4.57` is unblocked. `dns.avrig.ai` and `vault.avrig.ai` resolve accurately from Windows.
- Domain provisioning is a persistent initialization. If provisioning fails, stop before repeatedly re-running it. Inspect the resulting Samba databases and recover by preserving them or removing only the newly created, known-empty Samba state after explicit confirmation.
- Rauthy data is persistent under `/var/lib/rauthy/data`. Back it up before upgrades or destructive reset. Do not delete this directory as a troubleshooting shortcut.
- Rauthy listener is localhost-only. Google OAuth remains a separate follow-up requiring the OAuth client ID/secret and exact Rauthy callback URI.

---

## 7. Verification Checklist

- [x] Samba AD DC unit is enabled and active; no competing standalone Samba units.
- [x] `samba-tool domain info 127.0.0.1` reports the new `AVRIG.AI` domain.
- [x] Kerberos obtains a ticket for the domain Administrator without displaying the password.
- [x] SYSVOL and NETLOGON shares are present and readable by an authenticated domain account.
- [x] Integrated DNS answers AD locator records (`_ldap._tcp.dc._msdcs.avrig.ai`), the DC host record, and `dns.avrig.ai` A record.
- [x] Samba AD TCP/UDP listeners are restricted to loopback and current WSL `eth0`, not wildcard or LAN interfaces.
- [x] Windows NRPT routes only `avrig.ai` queries to current WSL `eth0`; pre-existing NRPT policy is unchanged; Windows resolves `dns.avrig.ai` through Samba.
- [x] Existing WSL DNS resolver configuration remains unchanged and external DNS behavior is not worsened.
- [x] Existing Vault and Vault Proxy services remain active and healthy.
- [x] Rauthy systemd-managed container is active; host binding is strictly `127.0.0.1:8443`.
- [x] Rauthy HTTPS health endpoint and OIDC discovery document return the configured issuer.
- [x] Rauthy data persists across a controlled service restart.
- [x] Samba and Rauthy credentials are outside the repository in `/root/avrig-ai-secrets/` and have restricted permissions.
- [x] Infrastructure baseline and project index document actual verified state.

---

## 8. Official References

- Samba AD DC provisioning: https://wiki.samba.org/index.php/Setting_up_Samba_as_an_Active_Directory_Domain_Controller
- Samba internal DNS backend: https://wiki.samba.org/index.php/Samba_Internal_DNS_Back_End
- Rauthy Getting Started: https://sebadob.github.io/rauthy/getting_started/main.html
- Rauthy container deployment: https://sebadob.github.io/rauthy/getting_started/docker.html
- Rauthy first-start credential handling: https://sebadob.github.io/rauthy/getting_started/first_start.html
- Rauthy bootstrap configuration: https://sebadob.github.io/rauthy/config/bootstrap.html
