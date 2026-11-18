---
title: "Plan: Direct Operator Preview Routing for Logged In Users on Launch Console"
status: completed
completed: 2026-11-16
created: 2026-11-16
author: avrig-ai
tags:
  - plan
  - fe
  - landing-page
  - auth
  - ux
---

# Plan: Direct Operator Preview Routing for Logged In Users on Launch Console

## Objective

Update the "Launch Console" action on the `avrig-ai` Landing Page so that if an operator is already logged in (authenticated via OIDC or active operator session flag), clicking "Launch Console" routes directly into the Operator Preview / Command Center without presenting the Login Modal. If unauthenticated, the Login Modal is displayed. Also ensure a clean logout lifecycle from the Command Center.

---

## Architectural Context & Decision Baseline

1. **Session & Auth Detection:**
   - Detect authenticated state using `useAuth()` (`auth.isAuthenticated`, `auth.user`) and persistent operator state (`localStorage.getItem("avrig-logged-in")`).
   - If `isLoggedIn === true`: "Launch Console" and the primary Hero CTA execute `onEnterCommandCenter()` directly.
   - If `isLoggedIn === false`: "Launch Console" triggers the `LoginModal`.
2. **Session Persistence & Clean Sign-Out:**
   - Entering operator preview saves the session flag (`localStorage.setItem("avrig-logged-in", "true")`).
   - Signing out from the Command Center clears the session flag (`localStorage.removeItem("avrig-logged-in")`) and resets operator state to return to the Landing Page.
3. **Subagent Delegation:**
   - Phase 1: Frontend updates in `LandingPage.tsx`, `App.tsx`, and `CommandCenterLayout.tsx` (Assignee: `fe`) - Completed
   - Phase 2: Build verification & deployment to `/var/www/web.avrig.ai` (Assignee: `fe` & `Infra`) - Completed
   - Phase 3: Live Browser Verification in dev mode (Assignee: `primary`) - Completed

---

## Verification Outcome

1. **Unauthenticated Check:**
   - Clicked "Launch Console" without an active session -> Login Dialog correctly displayed.
2. **Direct Routing when Logged In:**
   - With an active session flag, clicking "Launch Console" navigated directly to the Operator Preview / Command Center without opening the modal.
3. **Sign Out Lifecycle:**
   - Clicking Sign Out in the Command Center cleared the session flag and returned to the Landing Page. Subsequent click on "Launch Console" prompted the Login Modal as expected.
4. **Dev Server:**
   - Vite development server active on `http://localhost:3000/` with live HMR.
