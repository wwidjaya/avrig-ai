---
name: wmux
description: Windows terminal multiplexer (wmux) CLI for workspace management, pane and surface control, and built-in browser automation (open, snapshot, click, fill, type, get-text, eval, wait, screenshot, reload).
---

# wmux

Control wmux sessions, surfaces, panes, and embedded browser automation using the `wmux` CLI.

## How wmux Routes Browser Commands

When running inside a wmux terminal pane:
- `$env:WMUX_SURFACE_ID` is automatically set to the current terminal surface.
- `wmux browser ...` uses this terminal surface as `caller` to find and drive that pane's browser.
- If no browser exists yet for the caller, `wmux browser open <url>` automatically splits the pane and connects the browser.
- **Do not pass a browser surface ID to `--surface`**: `--surface` specifies the *terminal caller* pane, not the browser surface itself. Passing a browser ID makes wmux treat it as an unknown caller and spawn a redundant pane.

## Workspace & Surface Management

```powershell
# Inspect surfaces and find active browser / terminal surface IDs
wmux list-surfaces

# Workspaces
wmux list-workspaces
wmux new-workspace
wmux select-workspace <id>

# Create or split surfaces manually
wmux new-surface --type browser
wmux split --down --type browser
wmux split --type terminal

# Surface focus and lifecycle
wmux focus-surface <id>
wmux close-surface <id>
```

## Browser Automation

### Navigation & Inspection

```powershell
# Open or navigate to URL
wmux browser open https://example.com

# Accessibility tree snapshot with eN element references
wmux browser snapshot

# Read text from element or page
wmux browser get-text [ref]

# Take screenshot
wmux browser screenshot [--full]
```

### Element Interaction & Sharp Edges

- **Write refs bare (`e12` instead of `@e12`)**: In PowerShell, `@` triggers splatting or array syntax.
- **Run snapshot before interacting**: Refs require a preceding `snapshot` call to populate the tree cache.
- **Eval quoting in PowerShell**: Use JavaScript template literals (backticks) for strings inside PowerShell single quotes:
  ```powershell
  wmux browser eval '(() => { const el = document.querySelector(`input[type=email]`); return el.value; })()'
  ```
- **React controlled inputs**: Direct `.value` assignment is ignored by React forms. Use the native setter inside `eval` to trigger state updates:
  ```powershell
  wmux browser eval '(() => { const set = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, `value`).set; const el = document.querySelector(`input[type=password]`); set.call(el, `secret`); el.dispatchEvent(new Event(`input`, { bubbles: true })); })()'
  ```

```powershell
# Click element by bare ref
wmux browser click e1

# Fill or type text into inputs
wmux browser fill e2 "search text"
wmux browser type e2 "append text"

# Wait for element or timeout in ms
wmux browser wait e1 5000

# Execute JavaScript
wmux browser eval '(() => document.title)()'

# Navigation controls
wmux browser back
wmux browser forward
wmux browser reload

# Switch or view browser engine (web or agent)
wmux browser engine [web|agent]
```

## Terminal & Telemetry

```powershell
# Send commands or keys to terminal pane
wmux send "npm test"
wmux send-key Enter

# Inspect screen contents or agent prompt history
wmux read-screen [--lines 50]
wmux prompts [--limit 10]
```
