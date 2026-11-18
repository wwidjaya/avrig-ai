---
name: manage-keycloak
description: Manage the Keycloak IdP on the WSL `research` instance (systemd service, Postgres-backed). List/inspect/create user federation (LDAP/AD) components and realms, configure custom login themes, error message bundles, and internationalization (i18n), and copy a user federation connector between realms via `kcadm.sh`. Use when asked to manage Keycloak realms, user federation, LDAP providers, login themes, or localization.
---

# manage-keycloak

Manages the Keycloak Identity & Access Management instance running on the WSL `research` instance.

## Infrastructure

| Component | Location |
|-----------|----------|
| Keycloak install | `/opt/keycloak` (systemd service `keycloak.service`, user `keycloak`) |
| Admin CLI | `/opt/keycloak/bin/kcadm.sh` |
| kcadm token cache | `/home/keycloak/.keycloak/kcadm.config` (per-user, owner `keycloak`) |
| Admin console | `https://auth.wirianto.ai/admin/master/console/` |
| Database | PostgreSQL `keycloak` db on `127.0.0.1:5432` (user `keycloak`) |

## Access

All commands run inside the WSL instance `research`:

- **Windows:** `wsl -d research -- bash -lc "<command>"`
- **WSL/Linux:** `bash -lc "<command>"` inside the `research` instance

Run kcadm as the `keycloak` user (it owns `/opt/keycloak` and the token cache):

```bash
wsl -d research -- bash -lc 'sudo -u keycloak /opt/keycloak/bin/kcadm.sh <args>'
```

## Auth

Authenticate against the `master` realm. The working admin principal is user `admin` (email `admin@wirianto.ai`).

```bash
wsl -d research -- bash -lc 'sudo -u keycloak /opt/keycloak/bin/kcadm.sh config credentials \
  --server http://127.0.0.1:8080 --realm master --user admin --password "P1a0dRxhEZpQWgYFRae2DaCD"'
```

Gotchas:

- Admin user is **`admin`** in the `master` realm. The older `wwidjaya@gmail.com` credential documented elsewhere is stale and will be rejected (`invalid_grant`).
- The kcadm token in `/home/keycloak/.keycloak/kcadm.config` **expires** (default ~1h access + ~30min refresh). Re-run `config credentials` each session.
- `master` (admin realm), `kb`, `agentic`, and `researcher` are the current realms. There is **no** realm literally named `research` — the AD-federated realm is **`researcher`**.

## Common operations

### List realms

```bash
wsl -d research -- bash -lc 'sudo -u keycloak /opt/keycloak/bin/kcadm.sh get realms 2>&1 | grep -E "realm|enabled"'
```

### List a realm's components (keys, user federation, client registration policies)

```bash
wsl -d research -- bash -lc 'sudo -u keycloak /opt/keycloak/bin/kcadm.sh get components -r <realm>'
```

### Find user federation (LDAP) providers + mappers in a realm

```bash
wsl -d research -- bash -lc 'sudo -u keycloak /opt/keycloak/bin/kcadm.sh get components -r <realm> | python3 -c "import sys,json; data=json.load(sys.stdin); [print(c[\"providerType\"].split(\".\")[-1], \"|\", c[\"name\"], \"|\", c[\"providerId\"], \"|\", c[\"id\"], \"| parent\", c[\"parentId\"]) for c in data if c[\"providerType\"] in (\"org.keycloak.storage.UserStorageProvider\",\"org.keycloak.storage.ldap.mappers.LDAPStorageMapper\")]"'
```

### Query users (triggers live LDAP lookup for federated realms)

```bash
wsl -d research -- bash -lc 'sudo -u keycloak /opt/keycloak/bin/kcadm.sh get users -r <realm> -q username=<sAMAccountName>'
```

## Copy a user federation connector between realms

The AD LDAP provider in the `researcher` realm (`DC1 (wirianto.ai)`) federates the Samba AD at `ldaps://dc1.wirianto.ai:636`. `agentic` (and any new realm) can reuse it by copying the provider + its child LDAP mappers.

General steps:

1. **Auth** (see above) as `admin`.
2. **Resolve realm ids** (component `parentId` = realm id):
   - `researcher` = `b36fb574-c37a-4e26-b8e5-ebffbfbd2f32`
   - `agentic` = `32c1d723-a79e-46e3-85e1-b1e0a0136188`
3. **Create the LDAP provider** in the target realm with the source provider's config (parentId = target realm id, `bindCredential` = `password.123`), then capture the returned new component `id`.
4. **Copy each child LDAP mapper** that is parented to the source provider, changing only `parentId` to the **new** provider id.
5. **Delete auto-provisioned default mappers**: creating an LDAP provider programmatically makes Keycloak auto-attach default mappers (e.g. `full name`, plus duplicate `creation date`/`last name`/`email`/`username`/`modify date`/`MSAD account controls`/`Kerberos`). To mirror the source cleanly, delete any mapper **not** explicitly copied.
6. **Verify**: list the target realm's user federation components, then query a known AD user to confirm live LDAP resolution:
   ```bash
   wsl -d research -- bash -lc 'sudo -u keycloak /opt/keycloak/bin/kcadm.sh get users -r <target> -q username=wirianto.widjaja'
   ```

### Reference: `researcher` → `agentic` source provider config

Provider: name `DC1  (wirianto.ai)`, providerId `ldap`, providerType `org.keycloak.storage.UserStorageProvider`:

| Key | Value |
|-----|-------|
| `connectionUrl` | `ldaps://dc1.wirianto.ai:636` |
| `usersDn` | `OU=Employees,OU=Users,OU=Tier-2,DC=wirianto,DC=ai` |
| `bindDn` | `CN=Reader Service,OU=Infrastructure,OU=Service-Accounts,OU=Tier-1,DC=wirianto,DC=ai` |
| `bindCredential` | `password.123` |
| `vendor` | `ad` |
| `usernameLDAPAttribute` | `sAMAccountName` |
| `uuidLDAPAttribute` | `objectGUID` |
| `rdnLDAPAttribute` | `cn` |
| `userObjectClasses` | `person, organizationalPerson, user` |
| `krbPrincipalAttribute` | `userPrincipalName` |
| `editMode` | `READ_ONLY` |
| `importEnabled` | `false` |
| `searchScope` | `2` |
| `useTruststoreSpi` | `always` |
| `authType` | `simple` |
| `startTls` | `false` |
| `connectionTimeout` / `readTimeout` | `2000` |
| `connectProState` / sync | `fullSyncPeriod -1`, `changedSyncPeriod -1` |
| `cachePolicy` | `DEFAULT` |
| `priority` | `0` |

The 10 child mappers (parented to the provider):

1. `MSAD account controls` — `msad-user-account-control-mapper`
2. `username-cn` — `user-attribute-ldap-mapper` (cn → username)
3. `username` — `user-attribute-ldap-mapper` (sAMAccountName → username)
4. `first name` — `user-attribute-ldap-mapper` (givenName → firstName)
5. `Kerberos principal attribute mapper` — `kerberos-principal-attribute-mapper`
6. `email` — `user-attribute-ldap-mapper` (mail → email)
7. `last name` — `user-attribute-ldap-mapper` (sn → lastName)
8. `group` — `group-ldap-mapper` (groups DN `OU=Business,OU=Groups,DC=wirianto,DC=ai`, mode `LDAP_ONLY`, memberOf strategy)
9. `creation date` — `user-attribute-ldap-mapper` (whenCreated → createTimestamp)
10. `modify date` — `user-attribute-ldap-mapper` (whenChanged → modifyTimestamp)

## Theme & Localization Customization

Theme files live on WSL `research` at `/opt/keycloak/themes/<theme>/login/`. File permissions must be owned by `keycloak:keycloak`.

### Theme structure

```text
/opt/keycloak/themes/<theme>/login/
├── theme.properties
├── template.ftl
├── login.ftl
├── error.ftl
├── resources/
│   ├── css/login.css
│   └── img/logo.svg
└── messages/
    ├── messages_en.properties
    └── messages_id.properties
```

### Configure `theme.properties`

```properties
parent=base
import=common/keycloak
styles=css/login.css?v=2
meta=viewport==width=device-width,initial-scale=1
locales=en,id
```

### Override message bundles

Override error keys and label texts in `messages/messages_<locale>.properties`.

**`messages_en.properties`**:
```properties
invalidUserMessage=Invalid username or password.
invalidPasswordMessage=Invalid username or password.
invalidUsernameMessage=Invalid username or password.
accountDisabledMessage=Your account has been disabled.
```

**`messages_id.properties`**:
```properties
invalidUserMessage=Nama pengguna atau kata sandi yang Anda masukkan salah.
invalidPasswordMessage=Nama pengguna atau kata sandi yang Anda masukkan salah.
invalidUsernameMessage=Nama pengguna atau kata sandi yang Anda masukkan salah.
accountDisabledMessage=Akun Anda telah dinonaktifkan.
```

### Realm theme and localization CLI commands

Authenticate as `admin` in `master` first, then run:

```bash
# Enable internationalization, supported locales, and default locale
wsl -d research -- bash -lc 'sudo -u keycloak /opt/keycloak/bin/kcadm.sh update realms/<realm> \
  -s internationalizationEnabled=true \
  -s "supportedLocales+=en" \
  -s "supportedLocales+=id" \
  -s defaultLocale=en'

# Assign custom login theme to realm
wsl -d research -- bash -lc 'sudo -u keycloak /opt/keycloak/bin/kcadm.sh update realms/<realm> \
  -s loginTheme=<theme>'
```

### Apply changes & theme cache

Keycloak caches theme files in production mode. After modifying templates or message bundles, restart the systemd service:

```bash
wsl -d research -- bash -lc 'sudo systemctl restart keycloak'
```

## Gotchas

- No realm named `research` exists — the AD-federated realm is `researcher`.
- The admin password (`P1a0dRxhEZpQWgYFRae2DaCD`) is for user `admin` in `master`, not `wwidjaya@gmail.com`.
- The LDAP federation bind credential is `password.123` (matches the Samba AD admin password used by the `manage-dns` / `read-ldap` skills).
- kcadm requires `sudo -u keycloak`; running as root without HOME set breaks the token cache.
- `GET components` masks `bindCredential`. Read it from Postgres if needed:
  `select value from component_config where component_id='<provider-id>' and name='bindCredential';`
- Creating an LDAP provider auto-adds default mappers — always check for duplicates and clean up to mirror the source realm.
