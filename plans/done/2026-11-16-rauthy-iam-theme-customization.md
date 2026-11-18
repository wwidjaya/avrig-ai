---
title: "Plan: Customizing the Rauthy IAM Login Experience for avrig.ai"
status: completed
completed: 2026-11-16
created: 2026-11-16
author: avrig-ai
tags:
  - plan
  - iam
  - rauthy
  - oidc
  - nginx
  - theming
---

# Plan: Customizing the Rauthy IAM Login Experience for avrig.ai

> Superseded during implementation: the shipped design is a monochrome surface system with a blue action accent, not the glassmorphism/ambient-glow treatment described in steps 1-3. See "Execution Outcome" below.

## Objective

Customize the **Rauthy IAM** login interface (`https://iam.avrig.ai`) to match the **`avrig.ai`** visual design system (dark/light theme, modern card geometry, typography, and logo branding), while preserving native OAuth 2.1 / OpenID Connect Core 1.0 Authorization Code Flow with PKCE, WebAuthn Passkeys, and multi-provider portability.

---

## Architectural Context & Decision Baseline

1. **Authentication Protocol Invariant:**
   - Standard OIDC Authorization Code Flow with PKCE (`code_challenge_method=S256`) is retained.
   - The client application (`avrig.ai`) never handles, stores, or transmits raw user passwords (in strict compliance with OAuth 2.1 Section 4.3 deprecation of ROPC).
   - Preserves WebAuthn / Passkey origin security (`https://iam.avrig.ai`), hardware tokens, and anti-bot Proof-of-Work (POW) verification.
2. **Delivery Mechanism via Nginx Reverse Proxy:**
   - Rauthy runs within an immutable rootless container (`ghcr.io/sebadob/rauthy:0.37.2`).
   - The reverse proxy `iam.avrig.ai` terminates TLS on Nginx (Ubuntu 24.04 with compiled `http_sub_module`).
   - We utilize Nginx's `sub_filter` to dynamically inject a custom CSS stylesheet (`/custom/avrig-rauthy-theme.css`) and vector favicon into the response, ensuring persistence across container updates and restarts.

---

## Implementation Steps

### 1. Static Assets & Custom Theme Stylesheet (Assignee: fe)
- Create `/var/www/iam-custom/avrig-rauthy-theme.css` in WSL with custom design tokens matching `avrig.ai`:
  - **Dark background:** `hsl(240 10% 3.9%)` (`#09090b`) with subtle ambient radial glow.
  - **High-contrast cards:** `hsl(240 3.7% 15.9%)` (`#18181b`) with border `hsl(240 3.7% 25%)` and `backdrop-filter: blur(16px)`.
  - **Brand action colors:** Indigo `hsl(221.2 83.2% 53.3%)` (`#3b82f6`) with glowing hover states.
  - **Rounded borders:** Modern `0.75rem` (`12px`) geometry matching `@avrig/ui` (shadcn).
  - **Typography & Inputs:** Refined focus rings, smoothed fonts, and clean padding.
- Create `/var/www/iam-custom/avrig-logo.svg` representing the vector `avrig.ai` brand mark.

### 2. Nginx Reverse Proxy Configuration (Assignee: Infra)
- Edit `/etc/nginx/sites-available/iam.avrig.ai.conf`:
  - Configure `/custom/` static alias mapped to `/var/www/iam-custom/` with caching headers.
  - Set `proxy_set_header Accept-Encoding "";` to allow uncompressed HTML stream inspection.
  - Enable `sub_filter_types text/html;` and `sub_filter_once off;`.
  - Inject the theme stylesheet and logo:
    ```nginx
    sub_filter '</head>' '<link rel="stylesheet" href="/custom/avrig-rauthy-theme.css"><link rel="icon" href="/custom/avrig-logo.svg"></head>';
    ```
- Verify syntax with `nginx -t` and reload `nginx` without dropping connections.

### 3. Verification & Browser Visual Inspection (Assignee: fe)
- Execute `curl -i -k https://iam.avrig.ai/auth/v1/` and verify that `avrig-rauthy-theme.css` is injected in the HTML header.
- Execute browser automation (Playwright) to capture screenshots of `https://iam.avrig.ai/auth/v1/`:
  - Inspect Dark Mode visual fidelity and contrast.
  - Inspect Light Mode toggle and responsiveness.
- Perform a live OIDC login test from `https://avrig.ai` to ensure the redirect handshake completes with zero regression.

---

## Out of Scope
- Direct tampering with Rauthy's compiled internal WASM binaries.
- Disabling Rauthy's Proof-of-Work (POW) bot protection.
- In-memory credential harvesting or ROPC direct password endpoints.

---

## Execution Outcome (2026-11-16)

The theme shipped, but not as designed. Steps 1 through 3 above describe a glassmorphism direction: blurred translucent cards, an ambient radial glow, and glowing indigo hover states. What actually shipped is a monochrome surface system with a single blue action accent. The original steps are left unchanged as a record of the plan as written; the sections below record what was delivered.

### Delivered Assets

The stylesheet and the brand marks now live in the repository under `apps/web/public/` as `avrig-rauthy-theme.css`, `avrig-mark.svg`, and `avrig-logo.svg`, so they are versioned with the app rather than existing only on the server. They are deployed to `/var/www/iam-custom/` on the WSL instance `avrig-ai`, owned by `www-data:www-data` with mode 0644.

| Asset | Size | Notes |
| --- | --- | --- |
| `avrig-rauthy-theme.css` | 19,617 bytes | Grew from the previous 7,489 byte file. sha256 `6b1cfa0092586d0317b6c9ad169f5846620c47454d33497060c4080e1203247d`. |
| `avrig-mark.svg` | 676 bytes | The 32x32 brand mark. |
| `avrig-logo.svg` | 676 bytes | The same 32x32 mark, differing only in the gradient id. |

The stylesheet is byte-identical in the repository, on disk at `/var/www/iam-custom/`, and as served over HTTPS. `rauthy_dark.svg` and `rauthy_light.svg` in `/var/www/iam-custom/` were overwritten with the same mark, so every Rauthy logo slot resolves to the one brand mark instead of Rauthy's stock artwork.

### Nginx Changes

Exactly two hunks changed in `/etc/nginx/sites-available/iam.avrig.ai.conf`:

1. The `/custom/` cache policy moved from `expires 30d` plus `public, no-transform` to a single `Cache-Control: public, max-age=300, must-revalidate`.
2. The `sub_filter` injection now appends `?v=20261116a` to the stylesheet href, so a cached copy of the old theme cannot be reused after the swap.

`sub_filter_types` and the `Accept-Encoding` handling were deliberately left untouched.

### Rauthy Untouched

Rauthy itself was not modified. There is no `rauthy.toml` edit and no service restart. The Rauthy service uptime predates the change; only nginx was reloaded.

### Verification

- The SSR login page was fetched with `Accept-Language` set to `en` and to `de`. Both returned HTTP 200 with the injection present, including `<div class="outer` and the POST form.
- The versioned stylesheet returned 200 with `text/css` and the expected cache header.
- Both SVG marks returned 200 with `image/svg+xml`.
- `nginx -t` reported a clean configuration, and the nginx error log gained no new entries.
- Live screenshots of the login page at 1280x900 were captured in both dark and light themes.

### Design Decisions That Differ From the Plan

The palette is `#0a0a0b` for the canvas and `#101114` for cards, with `#3b82f6` and `#2563eb` as the accent pair. There is no glassmorphism and no radial glow: cards are opaque surfaces separated by borders and small elevation steps.

Rauthy's own color tokens are remapped rather than only styling the login markup, so native widgets such as the dialog, popover, and error text stay in the same palette instead of falling back to Rauthy's defaults.

Several pieces of copy have no DOM node in Rauthy's markup: the brand tagline, the `0.1 · Sovereign IAM` subline, the `Sign in to continue` subtitle, and the footer. These are emitted through `::before` and `::after` pseudo-elements instead. The theme switch and language selector were moved out of the bottom-left corner into a fixed top-right cluster.

### Constraints Discovered

- The page CSP allows only `'self'` styles and scripts, which rules out webfonts and any injected JavaScript.
- Rauthy's stashed `svelte-*` class names are avoided as selectors, with one documented fallback for the language selector.
- Rauthy pins the email wrapper to an inline `width: 18rem`, which had to be overridden to full width.

### Not Verified

A full credential login round-trip starting from `https://avrig.ai` was not exercised in this work. The change is CSS and static assets only, with no effect on the OIDC endpoints, tokens, PKCE, or WebAuthn, but a real sign-in from the web app remains a manual check.

### Rollback

Restore `/var/backups/iam-custom-20261116-1221.tar.gz` into `/var/www` and restore `/etc/nginx/sites-available/iam.avrig.ai.conf.bak-20261116-1221`, then run `nginx -t` and reload nginx. A later backup exists that covers the cache-policy hunk.

