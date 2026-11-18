---
title: "Plan: Web App Logout Screen and OIDC End-Session Flow"
status: completed
created: 2026-11-17
author: avrig-ai
tags:
  - plan
  - frontend
  - oidc
  - auth
  - react
  - rauthy
  - ux
---

# Plan: Web App Logout Screen and OIDC End-Session Flow

## 1. Problem Diagnosis & Objective

In `apps/web`:
1. **Incomplete OIDC End Session Flow**: 
   When the user clicks the Sign Out button in `CommandCenterLayout.tsx`, the application only invokes `auth.removeUser()` and clears client storage. It does not invoke OIDC RP-Initiated Logout (`auth.signoutRedirect()`). As a result, the upstream IdP session (Rauthy at `iam.avrig.ai`, which publishes `end_session_endpoint: "https://iam.avrig.ai/auth/v1/oidc/logout"`) remains fully active. If the user clicks "Login" or "Launch Console" again, Rauthy immediately auto-authenticates without prompting for credentials or account selection.
2. **Missing Post-Logout Screen**:
   There is no dedicated confirmation view (`/#logged-out`) confirming that the operator's active session and cryptographic credentials have been securely terminated.
3. **Objective**:
   Implement standard OIDC RP-initiated logout redirection, client session cleanup, and a branded post-logout confirmation screen with options to re-authenticate or return to the landing page.

---

## 2. Architecture & Design

### A. Dedicated Post-Logout View (`LoggedOutView.tsx`)
Create `apps/web/src/modules/auth/LoggedOutView.tsx`:
- Rendered when `window.location.hash === "#logged-out"` or `viewMode === "logged-out"`.
- Clean card layout using `@avrig/ui` and Lucide icons:
  - Shield / Check icon indicating session termination.
  - Heading: "Session Ended" / "Operator Logged Out".
  - Subtext: "Your session and authentication tokens have been cleared from this browser."
  - Action buttons:
    1. **"Sign In Again"**: Calls `auth.signinRedirect()` to start a fresh OIDC authorization flow.
    2. **"Return to Home"**: Clears hash and routes back to the main landing page (`viewMode = "landing"`).

### B. Full RP-Initiated Logout in `UniversalAuthProvider` & `CommandCenterLayout`
1. **UniversalAuthProvider.tsx**:
   Ensure `post_logout_redirect_uri` resolves to `${currentOrigin}/#logged-out`.
2. **CommandCenterLayout.tsx**:
   Update `handleSignOut`:
   ```ts
   const handleSignOut = async () => {
     try {
       if (typeof window !== "undefined") {
         localStorage.removeItem("avrig-logged-in");
         localStorage.removeItem("avrig-operator-mode");
         sessionStorage.clear();
       }
       if (auth.isAuthenticated || auth.user) {
         await auth.signoutRedirect({
           post_logout_redirect_uri: `${window.location.origin}/#logged-out`,
         });
       } else {
         if (onSignOut) onSignOut();
         if (typeof window !== "undefined") {
           window.location.hash = "#logged-out";
         }
       }
     } catch (err) {
       console.warn("Signout error:", err);
       if (onSignOut) onSignOut();
       if (typeof window !== "undefined") {
         window.location.hash = "#logged-out";
       }
     }
   };
   ```

### C. Route State Management in `App.tsx`
Update `App.tsx`:
- Extend `viewMode` state type: `"landing" | "console" | "logged-out"`.
- Sync hash listener with `#logged-out` alongside `#console`.
- Render `<LoggedOutView />` when `viewMode === "logged-out"`.

---

## 3. Implementation Phases & Subagent Assignments

### Phase 1: Create `LoggedOutView` Component
**Assignee: fe**
1. Create `apps/web/src/modules/auth/LoggedOutView.tsx` with responsive layout, dark/light theme support, and clear call-to-action buttons.
2. Export the component for integration in `App.tsx`.

### Phase 2: Wire RP-Initiated Signout & State Cleanup
**Assignee: fe**
1. Update `apps/web/src/shared/auth/UniversalAuthProvider.tsx` to set `post_logout_redirect_uri` to `${currentOrigin}/#logged-out`.
2. Update `apps/web/src/shell/CommandCenterLayout.tsx` `handleSignOut` to execute `auth.signoutRedirect()` with error fallback.

### Phase 3: Update `App.tsx` View Navigation
**Assignee: fe**
1. Update `App.tsx` to handle `#logged-out` hash in initial state and `hashchange` listener.
2. Render `LoggedOutView` when `viewMode === "logged-out"`.
3. Provide callback handlers for re-authenticating and returning to home.

### Phase 4: Build Verification & E2E Automated Testing
**Assignee: fe**
1. **TypeScript & Bundle Verification**:
   - Run `pnpm --filter @avrig/web build` to verify clean build without compilation or typing errors.
2. **Automated Browser Verification (`bsk`)**:
   - Start active `bsk` browser session: `bsk session start`.
   - Navigate to local or production web app URL (`https://avrig.ai/#console` or `http://localhost:5173/#console`).
   - Take snapshot (`bsk snapshot`) and locate the Sign Out button (`@eN` reference or `button[title="Sign Out"]`).
   - Trigger sign out: `bsk click --session <id> "button[title='Sign Out']"`.
   - Verify network navigation to `iam.avrig.ai/auth/v1/oidc/logout` and return redirect to `/#logged-out`.
   - Inspect page state with `bsk snapshot --session <id>` to assert that `LoggedOutView` elements are mounted ("Session Ended", "Sign In Again", "Return to Home").
   - Click "Sign In Again" and verify browser lands on the active Rauthy login credentials form (`iam.avrig.ai/auth/v1/oidc/authorize`), confirming the session cookie was terminated and not silently resumed.
   - Click "Return to Home" and verify the landing page renders without error.
   - Close browser test session: `bsk session stop`.

---

## 4. Acceptance Criteria & Validation Gates

- Clicking the Sign Out button in the command center terminates both local client state and the upstream Rauthy IdP session.
- The browser successfully redirects through the IdP end-session endpoint and lands on `/#logged-out`.
- The dedicated `LoggedOutView` is displayed, confirming session termination.
- E2E automated test via `bsk` confirms:
  1. The sign out button triggers the logout flow.
  2. The `/#logged-out` view mounts properly.
  3. Clicking "Sign In Again" requires entering credentials at the IdP (no automatic session bypass).
  4. Clicking "Return to Home" returns cleanly to the landing page.
- TypeScript builds pass with zero errors.
