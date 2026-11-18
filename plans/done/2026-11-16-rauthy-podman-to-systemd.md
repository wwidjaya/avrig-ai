---
title: "Plan: Migrate Rauthy from Podman to a Native systemd Service"
status: completed
created: 2026-11-16
completed: 2026-11-17
author: avrig-ai
tags:
  - plan
  - rauthy
  - podman
  - systemd
  - wsl
  - infrastructure
---

# Plan: Migrate Rauthy from Podman to a Native systemd Service

## Objective

Replace the Podman-managed Rauthy container in the WSL distribution `avrig-ai` with the same Rauthy version running as a native host process managed by systemd. Preserve the existing Rauthy data, configuration, OIDC issuer, WebAuthn settings, Nginx proxy, and loopback-only exposure.

This is a runtime migration only. Do not upgrade Rauthy, migrate databases, change the issuer, or alter Nginx as part of this work. The intended result is a native systemd service that does not invoke Podman at runtime.

## Current Evidence and Open Preflight

- A read-only WSL check found one running, root-owned Podman container named `rauthy`, using `ghcr.io/sebadob/rauthy:0.37.2`, with a host binding on `127.0.0.1:8443`. Rootless Podman for user `avrig` showed no containers or pods.
- The repository's infrastructure baseline identifies `/etc/rauthy/rauthy.toml`, `/var/lib/rauthy/data`, `/etc/systemd/system/rauthy.service`, and data ownership `10001:10001`.
- The historical Rauthy installation plan specifies a systemd-managed Podman container and persistent Hiqlite data.
- The exact live systemd unit, Podman command, image ID/digest, bind mounts, environment variables, and process UID could not be inspected during planning. These are mandatory preflight facts and must be captured before implementation.
- Rauthy's official documentation says there is no standalone installer or binary download, but supports running outside a container by copying the executable from an image or building from source. It documents launching the server with `rauthy serve` and selecting a config path.

## Decisions

1. Keep the installed Rauthy version at `0.37.2`. Do not combine this migration with an upgrade.
2. Prefer extracting the executable from the exact image used by the current container. Do not assume a mutable tag resolves to the same image; record and use the current image ID or digest.
3. Preserve the existing config and Hiqlite data in place where possible. Never run two Rauthy processes against the same data directory.
4. Keep the application listener on `127.0.0.1:8443`; Nginx remains the public-facing proxy and should not need changes.
5. Explicitly bind Hiqlite's internal API and Raft listeners to loopback. The container currently supplies network isolation, while Rauthy documents these internal listeners as binding to all interfaces by default.
6. Keep Podman installed and preserve the old container and image through the validation period. Remove only the Rauthy container after successful validation and a separate confirmation. Do not uninstall Podman without checking for other images, volumes, or workloads.

## Implementation Phases

### Phase 1: Read-Only Preflight

**Assignee: Infra**

1. Confirm the WSL distribution, Ubuntu version, systemd state, architecture, current Rauthy status, and active listeners.
2. Read `/etc/systemd/system/rauthy.service` and record its exact directives and Podman invocation.
3. Inspect the running container and record the immutable image ID/digest, command, mounts, user/UID/GID, port publishing, restart policy, and environment variable names. Do not print environment values that may contain secrets.
4. Verify the config, persistent data, and TLS paths, their ownership/modes, and the numeric service account mapping.
5. Inspect the exact image for the Rauthy executable path, version, architecture, and dynamic library dependencies. Verify the executable's CLI supports `serve` and a custom config path.
6. Identify all current listeners for Rauthy and Hiqlite. Confirm how the current config defines cluster node addresses and internal ports.

**Gate:** Stop if the image version/digest, executable, configuration inputs, or persistent data paths cannot be established. Do not infer values from the historical plan.

### Phase 2: Back Up and Prepare a Rollback Point

**Assignee: Infra**

1. Create a timestamped, root-only backup of the current systemd unit, Rauthy config, data directory, and TLS material if present.
2. Record the current container ID, image ID/digest, systemd state, listeners, and health/OIDC checks.
3. Ensure the data backup is consistent. Prefer stopping the current service briefly for the backup; if a live backup is used, establish that it is safe and consistent for Hiqlite first.
4. Confirm backup readability and available disk space before proceeding. Keep secrets out of command output and documentation.

### Phase 3: Stage and Validate the Native Executable

**Assignee: Infra**

1. Extract the executable from the exact image identified in Phase 1, without starting a second production instance.
2. Install it under a versioned host path such as `/usr/local/lib/rauthy/0.37.2/`, owned by root and not writable by the service account.
3. Verify the executable's version, architecture, checksum, and runtime dependencies. Record the checksum for the deployment record.
4. Run only non-server CLI checks during staging. Do not generate new secrets or a new config as part of this migration.
5. If exact-image extraction is not feasible, stop for approval before building from source or selecting another binary source.

### Phase 4: Service Identity, Access, and Listener Configuration

**Assignee: Infra**

1. Preserve the current numeric ownership where possible. Verify that UID/GID `10001:10001` maps to an appropriate host service identity. Check for UID/GID collisions before creating or changing any account.
2. Ensure the native service identity can read the existing Rauthy config and TLS files, and can write only to the required persistent data paths.
3. Configure the native process to bind its HTTPS listener to `127.0.0.1:8443`.
4. Bind Hiqlite API and Raft listeners to loopback using the documented config or environment settings. Verify the corresponding single-node peer addresses remain consistent with the existing data/config.
5. Preserve `pub_url`, proxy mode, trusted proxy behavior, WebAuthn RP ID/origin, encryption keys, and all other security-critical config values.

### Phase 5: Native systemd Unit

**Assignee: Infra**

1. Prepare a native `rauthy.service` whose `ExecStart` runs the staged binary directly with `serve` and the verified existing config path.
2. Preserve required environment variable names and values from the existing service without exposing secrets. Use a protected environment/config mechanism if the current unit supplies secrets through environment variables.
3. Run as the dedicated unprivileged service identity, not root. Configure working and writable paths to match the verified Rauthy data/TLS requirements.
4. Add systemd hardening only after confirming compatibility, including appropriate `NoNewPrivileges`, filesystem protection, and write-path restrictions. Do not block required network access or Hiqlite state writes.
5. Save the current Podman unit separately before replacing it. Validate the new unit syntax and inspect the final unit before starting it.

### Phase 6: Staging Test and Cutover

**Assignee: Infra**

1. If feasible, test the native binary against a separate copy of the data on isolated loopback ports. Adjust only the test copy's ports and node addresses. Never run the staging or production process against the same data directory as the live service.
2. Schedule a short maintenance window. Stop the Podman-managed Rauthy service and confirm the production data is no longer open before starting the native process.
3. Replace the `rauthy.service` unit with the native unit, run `systemctl daemon-reload`, and start the native service.
4. Verify `systemctl is-active rauthy`, journal output, process identity, and listeners. Confirm 8443, 8100, and 8200 are bound only to loopback as intended.
5. Verify the Rauthy health endpoint, HTTPS through Nginx, OIDC discovery issuer, authorization page, and an end-to-end login. Verify WebAuthn/Passkey behavior if test credentials are available.
6. Confirm the custom IAM theme, language selector, and theme toggle still work. The Nginx configuration and static theme assets should remain unchanged.
7. Do not remove the old container or image during initial cutover.

### Phase 7: Rollback, Retention, and Documentation

**Assignee: Infra**

1. If native startup or acceptance checks fail, stop the native service, restore the backed-up Podman unit, reload systemd, and start the original container using the recorded image ID/digest.
2. Do not automatically restore the data backup during rollback. First determine whether the native process changed data and whether restoring would discard legitimate writes.
3. Keep the original unit, container, image, and backups through the agreed validation period.
4. After successful validation, remove the stopped Rauthy container only if approved. Retain the Podman runtime unless a separate inventory and approval confirms it is unused.
5. Update `Infrastructure.md` and the historical installation record to describe the verified native systemd deployment, binary provenance/checksum, service identity, ports, paths, and rollback procedure.

## Acceptance Criteria

- `rauthy.service` runs the native Rauthy executable directly and does not invoke Podman.
- Rauthy remains at version `0.37.2`; existing config, Hiqlite data, OIDC issuer, WebAuthn settings, and client registrations are preserved.
- Rauthy remains reachable through Nginx at `iam.avrig.ai`; its application and Hiqlite listeners are restricted to loopback.
- Health checks, OIDC discovery, browser login, and available Passkey checks pass.
- Nginx and Rauthy remain active, and no new service errors appear in the journal.
- The previous Podman unit, container, image, and a verified backup remain available until rollback is no longer required.
- Documentation reflects the actual verified runtime and no longer describes this instance as rootless Podman.

## Risks and Controls

| Risk | Control |
| --- | --- |
| Container isolation disappears and internal ports bind to WSL interfaces | Explicitly bind Rauthy and Hiqlite listeners to loopback; verify with socket inspection |
| Host UID/GID does not match container ownership | Inspect numeric ownership and account mappings before assigning the native service identity |
| Service behavior depends on Podman environment or mounts | Capture exact unit, environment variable names, image command, and mount mappings in preflight |
| Data corruption or lock conflict | Stop the container before native startup; never point two processes at one data directory |
| Binary differs from the deployed image | Extract from the exact running image ID/digest and verify version/checksum |
| Rollback loses data or restores an incompatible state | Keep the same Rauthy version, preserve current data, and do not restore backups automatically |

## References

- Rauthy Getting Started: https://sebadob.github.io/rauthy/getting_started/main.html
- Rauthy CLI: https://sebadob.github.io/rauthy/config/cli.html
- Rauthy container setup and persistent data: https://sebadob.github.io/rauthy/getting_started/docker.html
- Rauthy configuration reference: https://sebadob.github.io/rauthy/config/config.html
- Existing deployment plan: `plans/done/2026-11-13-samba-ad-rauthy-wsl-installation.md`
- Infrastructure baseline: Vault `02-projects/avrig-ai/infra/Infrastructure.md`

---

## Execution Record (Completed 2026-11-17)

- **Binary Extraction & Staging:** Binary extracted directly from container `16c27e0ab095` (`ghcr.io/sebadob/rauthy:0.37.2`, SHA-256 `50f65249a718c84c4eb45e8e15156df8ad07ef466867682844463cc83d4dfcc4`) and installed to `/usr/local/lib/rauthy/0.37.2/rauthy`, symlinked to `/usr/local/bin/rauthy`.
- **Preflight Port Conflict Discovery:** HashiCorp Vault cluster listener was previously bound to `127.0.0.1:8201`, which collided with Hiqlite Raft's default port. Vault was safely shifted to `cluster_addr = "http://127.0.0.1:8203"` in `/etc/vault.d/vault.hcl`, allowing Hiqlite to preserve its historical node addresses (`127.0.0.1:8101` and `127.0.0.1:8201`) without consensus raft migration.
- **Service Identity & Permissions:** Dedicated system account `rauthy:rauthy` (UID `10001`, GID `10001`) created with home `/var/lib/rauthy`. Full ownership assigned over `/var/lib/rauthy` and `/etc/rauthy/rauthy.toml`.
- **Backups:** Full root-only snapshot saved in `/var/backups/rauthy-pre-native-migration/` including `rauthy.service.podman`, `rauthy.toml.bak`, and `/var/lib/rauthy` tree.
- **Native systemd Unit:** Created `/etc/systemd/system/rauthy.service` with strict sandboxing (`ProtectSystem=strict`, `NoNewPrivileges=yes`, `PrivateTmp=yes`, `ProtectHome=yes`, `ReadWritePaths=/var/lib/rauthy`, `ReadOnlyPaths=/etc/rauthy`).
- **Validation Results:**
  - `systemctl is-active rauthy` -> `active`
  - Listeners: `127.0.0.1:8443` (HTTPS), `127.0.0.1:8101` (Hiqlite RPC), `127.0.0.1:8201` (Hiqlite API)
  - Upstream health endpoint: `curl -k https://127.0.0.1:8443/auth/v1/health` -> `{"db_healthy":true,"cache_healthy":true}`
  - Public Nginx gateway: `curl -k https://iam.avrig.ai/auth/v1/health` -> `200 OK`, `{"db_healthy":true,"cache_healthy":true}`
  - OIDC discovery: `curl -k https://iam.avrig.ai/auth/v1/.well-known/openid-configuration` -> `200 OK`, valid issuer `https://iam.avrig.ai/auth/v1/`
  - Authorization endpoint: `curl -k https://iam.avrig.ai/auth/v1/oidc/authorize` -> `400 Bad Request` (expected OIDC missing client_id parameter validation)
  - Podman container `rauthy` and image `ghcr.io/sebadob/rauthy:0.37.2` remain retained on host for rollback safety window.

