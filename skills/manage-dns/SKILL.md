---
name: manage-dns
description: Add, query, and delete records in Samba Active Directory DNS on a selected WSL instance. Supports caller-selected WSL distribution, DNS server, zone, record type, and record data.
---

# manage-dns

Manage DNS records in a Samba AD DNS server running in a selected WSL distribution. Do not assume a particular distribution, domain, DNS server address, zone, or record target. Confirm the target instance, zone, record name, type, and data before writes. A DNS A record identifies an IP address, not a service port.

## Access and target selection

On Windows, use the PowerShell wrapper:

```powershell
pwsh "$env:OPENCODE_CONFIG_DIR/shared/skills/manage-dns/dns.ps1" <add|query|delete> <name> [data] -Zone <zone> [-WslDist <distribution>] [-Server <dns-server>] [-Admin <account>] [-Type <record-type>]
```

Parameters:

- `-WslDist`: target WSL distribution. Default: `avrig-ai`.
- `-Server`: Samba DNS server address or DC FQDN as reachable from inside that distribution. Default: `wirianto-zb.avrig.ai`. (Note: when using Kerberos RPC, target the DC FQDN rather than `127.0.0.1` to match the Kerberos SPN).
- `-Zone`: DNS zone to update or query. Required, with no assumed domain.
- `-Admin`: Samba account name. Default: `Administrator`.
- `-Type`: DNS record type. Defaults are `A` for add, delete, and query.
- `data`: required for add and delete. The wrapper does not invent a destination IP.

The wrapper automatically detects if a local root-protected credentials store exists (e.g. `/root/avrig-ai-secrets/samba-admin-password`) to initialize a Kerberos ticket (`kinit`) and execute non-interactively via `--use-kerberos=desired`. If no credential file is present, Samba prompts interactively. It never prints passwords or exposes secrets in command arguments.

## Examples

Add an A record in `avrig.ai` on the `avrig-ai` WSL instance, targeting the current WSL interface address:

```powershell
pwsh "$env:OPENCODE_CONFIG_DIR/shared/skills/manage-dns/dns.ps1" add vault 172.26.4.57 -Zone avrig.ai -WslDist avrig-ai
```

Query a zone-relative name, or provide its fully qualified name in the selected zone:

```powershell
pwsh "$env:OPENCODE_CONFIG_DIR/shared/skills/manage-dns/dns.ps1" query vault -Zone avrig.ai -WslDist avrig-ai
pwsh "$env:OPENCODE_CONFIG_DIR/shared/skills/manage-dns/dns.ps1" query vault.avrig.ai -Zone avrig.ai -WslDist avrig-ai
```

Add or delete records in a different distribution and zone by explicitly selecting each:

```powershell
pwsh "$env:OPENCODE_CONFIG_DIR/shared/skills/manage-dns/dns.ps1" add portal 10.0.0.25 -Zone example.internal -WslDist ad -Server dc1.example.internal
pwsh "$env:OPENCODE_CONFIG_DIR/shared/skills/manage-dns/dns.ps1" delete portal 10.0.0.25 -Type A -Zone example.internal -WslDist ad -Server dc1.example.internal
```

The example IP values are illustrative. Check the active WSL address before using one because WSL interface addresses can change after restart.

## Direct Samba commands

Run inside the selected WSL instance. Authenticate with Kerberos TGT or interactively:

```bash
# Obtain Kerberos TGT
cat /root/avrig-ai-secrets/samba-admin-password | kinit Administrator@AVRIG.AI

# Query/Add/Delete targeting DC FQDN
samba-tool dns query wirianto-zb.avrig.ai avrig.ai vault A --use-kerberos=desired
samba-tool dns add wirianto-zb.avrig.ai avrig.ai test A 172.26.4.57 --use-kerberos=desired
samba-tool dns delete wirianto-zb.avrig.ai avrig.ai test A 172.26.4.57 --use-kerberos=desired
```

Replace the DNS server address, zone, relative name, type, data, and account for the selected environment. To run from Windows, prefix the command with `wsl.exe -d <distribution> --`.

## Record data formats

| Type | Data format |
| --- | --- |
| A | IPv4 address |
| AAAA | IPv6 address |
| PTR | Fully qualified domain name |
| CNAME | Fully qualified domain name |
| NS | Fully qualified domain name |
| MX | `"fully-qualified-name preference"` |
| SRV | `"fully-qualified-name port priority weight"` |
| TXT | Samba-compatible quoted TXT strings |

DNS query types also accept `SOA` and `ALL`.

## Validation and verification

- The wrapper requires an explicit zone and explicit data for add/delete. It normalizes an FQDN to a zone-relative name and rejects an FQDN outside the selected zone.
- Query an A record from Windows using the intended DNS server:

  ```powershell
  Resolve-DnsName vault.avrig.ai -Type A -Server <dns-server-ip>
  ```

- Or query directly inside WSL:

  ```bash
  dig @127.0.0.1 vault.avrig.ai A +noall +answer
  ```

- Delete requires the exact data value to remove. Inspect the existing record first and preserve backups or documented rollback details for important records.
- DNS updates to AD-integrated zones are immediate after a successful update.
- If Windows DNS requests time out and OpenVPN WFP filtering is a plausible cause, follow the `unblock-vpn` skill. Its Windows command changes WFP state, requires administrator elevation and operator confirmation, and must be followed by a DNS query verification. Do not substitute broad firewall or DNS policy changes.
