---
name: browser
description: Browser automation and E2E debugging using the bsk CLI.
---

# Browser Skill (`bsk`)

Browser automation and debugging tool for AI agents driving connected Chromium/Edge browser windows.

## Prerequisites & Daemon Management

Before starting a session, ensure the background daemon is active and the browser extension is connected:

```powershell
# Start the background daemon
bsk daemon start

# Check daemon health, port, and connected browser count
bsk status

# Diagnostics & extension connection links if 0 browsers connected
bsk doctor

# Stop or restart daemon when needed
bsk daemon stop
bsk daemon restart
```

## Standard Automation Workflow

1. **Start a session**:
   ```powershell
   bsk session start
   # Outputs session ID (e.g. `dwgb`)
   ```

2. **Navigate & inspect**:
   ```powershell
   # Navigate to target URL
   bsk navigate https://example.com --session <id>

   # Inspect semantic ARIA tree and get @eN element references
   bsk snapshot --session <id>

   # Capture visual viewport PNG
   bsk screenshot --session <id>
   ```

3. **Interact with elements**:
   ```powershell
   # Click element via snapshot ref (@eN) or CSS selector
   bsk click --session <id> "@e2"
   bsk click --session <id> "button.submit"

   # Fill input or textarea
   bsk fill --session <id> "@e1" "test@example.com"

   # Evaluate JavaScript expression
   bsk evaluate --session <id> "window.location.href"
   ```

4. **Debug & Telemetry**:
   ```powershell
   # View browser console errors and logs
   bsk console --session <id> --limit 20

   # View network requests and HTTP status codes
   bsk network --session <id> --limit 30

   # Reload current tab
   bsk reload --session <id>
   ```

5. **Clean up**:
   ```powershell
   # Stop the session
   bsk session stop <id>

   # Stop all active sessions
   bsk session stop --all
   ```

## Command Reference Summary

| Category | Command | Description |
|---|---|---|
| **Daemon** | `bsk daemon start` | Starts background service |
| | `bsk status` | Shows daemon status & connected browsers |
| | `bsk doctor` | Runs diagnostic health check |
| **Session** | `bsk session start` | Starts new browser session |
| | `bsk session list` | Lists active sessions |
| | `bsk session stop <id>` | Ends specific session |
| **Navigation** | `bsk navigate <url> --session <id>` | Opens URL in active window |
| | `bsk reload --session <id>` | Reloads active page |
| **Inspection** | `bsk snapshot --session <id>` | Outputs ARIA accessibility tree with `@eN` refs |
| | `bsk screenshot --session <id>` | Captures screenshot to temp PNG |
| | `bsk console --session <id>` | Inspects console logs/errors |
| | `bsk network --session <id>` | Inspects network responses/failures |
| **Interaction** | `bsk click --session <id> "<target>"` | Clicks `@eN` ref or CSS selector |
| | `bsk fill --session <id> "<target>" "<val>"` | Enters text into form control |
| | `bsk evaluate --session <id> "<js>"` | Runs JS expression in page context |
