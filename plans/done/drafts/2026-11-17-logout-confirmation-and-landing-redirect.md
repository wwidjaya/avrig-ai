---
title: "Plan: Logout Confirmation Dialog and Direct Landing Page Redirection"
status: superseded
superseded_by: 2026-11-18-release-0.3.0-consolidated.md
created: 2026-11-17
author: avrig-ai
tags:
  - plan
  - frontend
  - react
  - auth
  - oidc
  - deploy
  - wsl
---

# Plan: Logout Confirmation Dialog and Direct Landing Page Redirection

## 1. Objective

Update the Sign Out flow in `apps/web` so that:
1. Clicking the "Sign Out" button does not immediately disconnect the user; instead, it presents a confirmation dialog.
2. If confirmed, the session is cleared, authentication tokens/sessions are revoked or removed, and the application immediately transitions to the Landing Page (instead of displaying a separate logged-out screen).
3. If cancelled, the dialog closes and the user remains in the Command Center.
4. Verify changes via automated checks/tests and build bundle.
5. Deploy the updated production bundle to `/var/www/web.avrig.ai` inside the `avrig-ai` WSL distribution.

---

## 2. Implementation Phases & Subagent Assignments

### Phase 1: Frontend Confirmation Modal & Redirection (`Assignee: fe`)
1. **Modal Component & State in `apps/web/src/shell/CommandCenterLayout.tsx`**:
   - Add state `showLogoutConfirm: boolean` (default `false`).
   - Import `Dialog`, `DialogContent`, `DialogHeader`, `DialogTitle`, `DialogDescription`, and `DialogFooter` from `@avrig/ui`.
   - Update the Sign Out action button (`LogOut` icon in sidebar) to set `showLogoutConfirm = true`.
   - Implement the confirmation dialog:
     - **Title**: "Sign Out Confirmation"
     - **Description**: "Are you sure you want to sign out of avrig-ai Command Center and return to the main landing page?"
     - **Cancel Button**: Variant `outline` or `ghost`, closes the dialog.
     - **Confirm Button**: Variant `destructive`, triggers `handleSignOut`.
2. **Landing Page Redirection Flow**:
   - In `handleSignOut`:
     - Clean up client storage: remove `avrig-logged-in`, `avrig-operator-mode`, and clear `sessionStorage`.
     - In OIDC signout:
       - Set `post_logout_redirect_uri` to `${window.location.origin}/` (or clear hash directly).
       - When falling back to local signout or when OIDC redirect is not triggered, clear `window.location.hash = ""` (or navigate directly to landing view) and call `onSignOut()`.
   - In `apps/web/src/app/App.tsx`:
     - Ensure clearing hash or resetting auth directs the user to `"landing"` view mode cleanly.

### Phase 2: Build & Automated Testing (`Assignee: fe`)
1. Run linting / typecheck:
   ```powershell
   pnpm --filter @avrig/web typecheck
   ```
2. Run test suites:
   ```powershell
   pnpm --filter @avrig/web test
   ```
3. Run production build:
   ```powershell
   pnpm --filter @avrig/web build
   ```
4. Verify `apps/web/dist` outputs clean HTML/JS assets without warnings or errors.

### Phase 3: WSL Deployment & Service Verification (`Assignee: Infra`)
1. Sync built files to the WSL `avrig-ai` web server root:
   ```powershell
   wsl -d avrig-ai -- sudo cp -r /mnt/d/Cloud/OneDrive/AI/Agentic/avrig-ai/apps/web/dist/* /var/www/web.avrig.ai/
   wsl -d avrig-ai -- sudo chown -R www-data:www-data /var/www/web.avrig.ai
   ```
2. Verify Nginx status and endpoints:
   ```powershell
   wsl -d avrig-ai -- sudo systemctl status nginx
   curl -kI https://web.avrig.ai
   ```
3. Perform end-to-end user verification:
   - Access `https://web.avrig.ai/#console`.
   - Click Sign Out: verify confirmation dialog appears.
   - Click Cancel: verify dialog closes and session stays intact.
   - Click Confirm: verify session ends and user lands on the Landing Page directly.

---

## 3. Verification Criteria
- [ ] Sign Out button triggers confirmation modal.
- [ ] Cancelling retains operator session without navigating away.
- [ ] Confirming logs out and redirects directly to the landing page.
- [ ] `pnpm --filter @avrig/web build` completes with zero errors.
- [ ] Assets are deployed to `/var/www/web.avrig.ai` in WSL and served by Nginx.
