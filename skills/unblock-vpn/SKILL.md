---
name: unblock-vpn
description: Unblocks OpenVPN WFP filters that may block port 53 traffic for specified target IPs (defaults to 172.26.0.50, or takes an explicit IP).
---

# Skill: unblock-vpn

Unblocks the OpenVPN WFP filters that may be blocking port 53 traffic. Use this skill when DNS queries from the host or `nslookup` fail, and it is suspected that OpenVPN leak protection is interfering.

## Access

All commands run on the Windows host system (not inside WSL).

- **Default Command:** `D:\Development\kb\scripts\unblock-openvpn\unblock-openvpn.exe install`
- **Parameterized Command:** `D:\Development\kb\scripts\unblock-openvpn\unblock-openvpn.exe install <target-ip>`

## Usage

Run this skill when you encounter "Request timed out" or "Connection refused" errors during DNS operations that are not related to server availability but appear to be network filtering issues.

- Default: `D:\Development\kb\scripts\unblock-openvpn\unblock-openvpn.exe install` (unblocks `172.26.0.50:53`)
- Custom target IP: `D:\Development\kb\scripts\unblock-openvpn\unblock-openvpn.exe install <target-ip>` (e.g. `172.26.4.57` for `avrig-ai`)
- Persist across reboot: `D:\Development\kb\scripts\unblock-openvpn\unblock-openvpn.exe install <target-ip> persist`
- Remove all filters: `D:\Development\kb\scripts\unblock-openvpn\unblock-openvpn.exe remove`
- List active filters: `D:\Development\kb\scripts\unblock-openvpn\unblock-openvpn.exe list`

