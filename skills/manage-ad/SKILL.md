---
name: manage-ad
description: Manage, read, write, and query the Samba Active Directory (AD, LDAP) in WSL instance `ad` (DC1, domain `wirianto.ai`). Inspect, search, create, modify, and delete users, groups, OUs, and service accounts. Includes arbitrary LDAP searches, directory inspection, and setting service account passwords to never expire.
---

# manage-ad

Manage and query the Samba Active Directory DC in WSL instance `ad` (hostname `dc1`, realm `WIRIANTO.AI`, base DN `DC=wirianto,DC=ai`).

## Access and Invocation

All operations execute in the WSL instance `ad`. The wrapper runs commands with root privileges against the local Samba database, avoiding authentication credential expiry and network binding overhead.

### Windows (PowerShell)

```powershell
pwsh $env:OPENCODE_CONFIG_DIR/shared/skills/manage-ad/manage-ad.ps1 <command...>
```

### WSL / Linux

```bash
bash $OPENCODE_CONFIG_DIR/shared/skills/manage-ad/manage-ad.sh <command...>
# or directly inside WSL 'ad':
sudo samba-tool <command...>
```

## Service Account and Password Expiration

### Make Service Account Password Never Expire

Run `user setexpiry` with `--noexpiry`. In Samba 4.19, this sets both `accountExpires: 0` and the `UF_DONT_EXPIRE_PASSWORD` flag (`0x10000` bitmask in `userAccountControl`):

```powershell
pwsh $env:OPENCODE_CONFIG_DIR/shared/skills/manage-ad/manage-ad.ps1 user setexpiry <username> --noexpiry
```

Example for reader service account:

```powershell
pwsh $env:OPENCODE_CONFIG_DIR/shared/skills/manage-ad/manage-ad.ps1 user setexpiry reader --noexpiry
```

### Set or Reset Account Password

```powershell
pwsh $env:OPENCODE_CONFIG_DIR/shared/skills/manage-ad/manage-ad.ps1 user setpassword <username> --newpassword="SecretPassword123"
```

### Verify Account and Password State

```powershell
pwsh $env:OPENCODE_CONFIG_DIR/shared/skills/manage-ad/manage-ad.ps1 user show <username>
```

Verify key attributes:
- `userAccountControl`: `66048` (`512` NORMAL_ACCOUNT + `65536` DONT_EXPIRE_PASSWORD)
- `accountExpires`: `0` (never expires)

## Query and Read Operations

### List Users

```powershell
pwsh $env:OPENCODE_CONFIG_DIR/shared/skills/manage-ad/manage-ad.ps1 user list
```

### Show User Details

```powershell
pwsh $env:OPENCODE_CONFIG_DIR/shared/skills/manage-ad/manage-ad.ps1 user show wirianto.widjaja
```

Key attributes: `sAMAccountName`, `userPrincipalName`, `mail`, `distinguishedName`, `memberOf`, `objectSid`, `userAccountControl` (512 = normal, 66048 = password never expires), `primaryGroupID` (513 = Domain Users).

### List Groups

```powershell
pwsh $env:OPENCODE_CONFIG_DIR/shared/skills/manage-ad/manage-ad.ps1 group list
```

### Show Group Details

```powershell
pwsh $env:OPENCODE_CONFIG_DIR/shared/skills/manage-ad/manage-ad.ps1 group show "Domain Users"
```

### List Group Members

```powershell
pwsh $env:OPENCODE_CONFIG_DIR/shared/skills/manage-ad/manage-ad.ps1 group listmembers "Domain Admins"
```

### List Organizational Units (OUs)

```powershell
pwsh $env:OPENCODE_CONFIG_DIR/shared/skills/manage-ad/manage-ad.ps1 ou list
```

### Domain Information and Password Policy

```powershell
pwsh $env:OPENCODE_CONFIG_DIR/shared/skills/manage-ad/manage-ad.ps1 domain info
pwsh $env:OPENCODE_CONFIG_DIR/shared/skills/manage-ad/manage-ad.ps1 domain passwordsettings show
```

### Arbitrary LDAP Search

Search using LDAP filter syntax against base DN `DC=wirianto,DC=ai`:

```powershell
pwsh $env:OPENCODE_CONFIG_DIR/shared/skills/manage-ad/manage-ad.ps1 search "(objectClass=user)" sAMAccountName mail
pwsh $env:OPENCODE_CONFIG_DIR/shared/skills/manage-ad/manage-ad.ps1 search "(objectClass=group)" cn
pwsh $env:OPENCODE_CONFIG_DIR/shared/skills/manage-ad/manage-ad.ps1 search "(&(objectClass=user)(mail=*@wirianto.ai))" sAMAccountName mail
```

## Write and Management Operations

### Create an OU

```powershell
pwsh $env:OPENCODE_CONFIG_DIR/shared/skills/manage-ad/manage-ad.ps1 ou create "OU=Research,DC=wirianto,DC=ai"
```

### Create a Group

```powershell
pwsh $env:OPENCODE_CONFIG_DIR/shared/skills/manage-ad/manage-ad.ps1 group add researcher --groupou="OU=Research,DC=wirianto,DC=ai"
```

### Create a User

```powershell
pwsh $env:OPENCODE_CONFIG_DIR/shared/skills/manage-ad/manage-ad.ps1 user create researcher "Password.123" --mail-address=researcher@wirianto.ai --given-name=Wirianto --surname=Widjaja --userou="OU=Research,DC=wirianto,DC=ai"
```

### Manage Group Membership

```powershell
# Add member
pwsh $env:OPENCODE_CONFIG_DIR/shared/skills/manage-ad/manage-ad.ps1 group addmembers researcher wirianto.widjaja

# Remove member
pwsh $env:OPENCODE_CONFIG_DIR/shared/skills/manage-ad/manage-ad.ps1 group removemembers researcher wirianto.widjaja
```

### Move Objects

```powershell
pwsh $env:OPENCODE_CONFIG_DIR/shared/skills/manage-ad/manage-ad.ps1 user move researcher "OU=Tier-2,DC=wirianto,DC=ai"
```

### Enable / Disable Accounts

```powershell
pwsh $env:OPENCODE_CONFIG_DIR/shared/skills/manage-ad/manage-ad.ps1 user disable researcher
pwsh $env:OPENCODE_CONFIG_DIR/shared/skills/manage-ad/manage-ad.ps1 user enable researcher
```

## Directory Structure Reference

The domain adheres to the Microsoft Tiered Administration Model:

```text
DC=wirianto,DC=ai
|-- OU=Domain Controllers        (holds DC1$ at root)
|-- OU=Tier-0                    (Privileged-Admins, Privileged-Workstations)
|-- OU=Tier-1                    (Servers [Infrastructure/Application/Database], Service-Accounts)
|-- OU=Tier-2                    (Users [Employees/Contractors], Workstations)
|-- OU=Groups                    (Business, Application, Infrastructure, Security)
`-- OU=Quarantine                (Users, Computers)
```
