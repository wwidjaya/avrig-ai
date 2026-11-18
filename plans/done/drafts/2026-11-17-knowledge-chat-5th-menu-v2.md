---
title: "Plan: Add Knowledge Chat as 5th Main Menu in Web Command Center"
status: planned
created: 2026-11-17
author: avrig-ai
tags:
  - plan
  - frontend
  - react
  - navigation
  - knowledge
  - chat
  - ui
---

# Plan: Add Knowledge Chat as 5th Main Menu in Web Command Center

## 1. Objective

Promote Knowledge Chat from being an internal tab of the Knowledge & Trace domain into a first-class, dedicated **5th top-level menu item** in the Command Center sidebar navigation (`ActiveDomain: "chat"`), giving operators direct, full-screen access to epistemic queries and document citations.

---

## 2. Implementation Phases & Subagent Assignments

### Phase 1: Frontend Domain & Sidebar Navigation Update (`Assignee: fe`)
1. **Extend `ActiveDomain` & `navItems` in `apps/web/src/shell/CommandCenterLayout.tsx`**:
   - Update domain type:
     ```ts
     export type ActiveDomain = "office" | "deliberations" | "sdlc" | "knowledge" | "chat";
     ```
   - Import `MessageSquareText` (or `Bot`) from `lucide-react`.
   - Add the 5th menu item to `navItems`:
     ```ts
     { id: "chat", label: "Knowledge Chat", icon: MessageSquareText, tag: "KM/AI" }
     ```
2. **Mount Standalone View in `apps/web/src/app/App.tsx`**:
   - Import `KnowledgeChat` component:
     ```tsx
     import { KnowledgeChat } from "../modules/knowledge/KnowledgeChat";
     ```
   - Render `KnowledgeChat` inside the command viewport when `activeDomain === "chat"`:
     ```tsx
     {activeDomain === "chat" && (
       <div className="flex flex-1 overflow-hidden p-6">
         <KnowledgeChat />
       </div>
     )}
     ```
   - Add Knowledge Chat option to the global Command Palette (`CommandPalette` under Navigation group) with shortcut/quick jump.
3. **Streamline `KnowledgeView.tsx`**:
   - Keep `KnowledgeView.tsx` focused on document catalog exploration, metadata inspection, and cryptographic graph lineage.

### Phase 2: Build & Verification (`Assignee: fe`)
1. Run typecheck:
   ```powershell
   pnpm --filter @avrig/web typecheck
   ```
2. Run production build:
   ```powershell
   pnpm --filter @avrig/web build
   ```
3. Ensure zero compilation or bundling errors and that `apps/web/dist` outputs updated chunks.

### Phase 3: WSL Deployment & Service Verification (`Assignee: Infra`)
1. Sync built artifacts from `apps/web/dist` to `/var/www/web.avrig.ai/` on WSL distro `avrig-ai`:
   ```bash
   sudo rsync -av --delete /mnt/d/Cloud/OneDrive/AI/Agentic/avrig-ai/apps/web/dist/ /var/www/web.avrig.ai/
   sudo chown -R www-data:www-data /var/www/web.avrig.ai && sudo chmod -R 755 /var/www/web.avrig.ai
   ```
2. Verify live deployment with `curl -k -I https://web.avrig.ai`.
3. Validate user experience:
   - Sidebar renders 5 distinct menu items.
   - Clicking "Knowledge Chat" switches to the dedicated chat workspace.
   - Command Palette includes the new item.

---

## 3. Verification Criteria
- [ ] Sidebar exhibits 5 navigation items:
  1. Office & Org (`OG/WF`)
  2. Deliberation Rooms (`MT`)
  3. SDLC Pipeline (`RE-TE`)
  4. Knowledge & Trace (`KM/TR`)
  5. Knowledge Chat (`KM/AI`)
- [ ] Selecting "Knowledge Chat" renders the full-height epistemic query assistant.
- [ ] Command Palette (`Ctrl+K`) navigates cleanly to Knowledge Chat.
- [ ] `pnpm --filter @avrig/web build` succeeds with 0 errors.
- [ ] Deployed to `/var/www/web.avrig.ai` on WSL `avrig-ai` and verified.
