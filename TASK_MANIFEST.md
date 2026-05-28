
# 📜 HERMES WEBUI: IMPLEMENTATION MANIFEST (V2 - SOVEREIGN DEBT EDITION)
**Sovereign State:** Industrial Mirror (Emerald-on-Black)
**Project Root:** /root/hermes-webui

## 🚩 GLOBAL CONSTRAINTS (MANDATORY)
1. FORBIDDEN: No GitHub/Remote Repos. Implement LOCAL files only.
2. FORBIDDEN: No generic placeholders. Logic must be functional.
3. REQUIRED: All UI changes must maintain the Emerald-on-Black Hardware Mirror aesthetic.
4. REQUIRED: Use `write_file` and `patch` for all changes.

## 🛠️ THE FUNCTIONAL GAP (Sovereign Debt)

### 🟢 TOOL-CALL VISUALIZATION (High Priority)
- [ ] **The Tool Card:** Modify the chat loop to detect JSON tool calls in the stream.
- [ ] **Visual Rendering:** Create a dedicated `.tool-card` CSS style with an expandable "Arguments" dropdown and a "Result" block.
- [ ] **Real-time Update:** Tool cards must appear *while* the agent is thinking, not just at the end.

### 🟢 MEMORY CURATION (High Priority)
- [ la la **Sovereign Memory View:** Implement a la lytout in `/api/memory` that lists all curated facts.
- [ ] **Curation Interface:** Add the ability to "delete" or "edit" a memory fact via a POST request.
- [ ] **Vector Visualization:** a lytout a simple canvas-based node map of the vector memory space.

### 🟢 KANBAN DISPATCHER (Medium Priority)
- [ ] **Auto-Siphon:** Implement logic where moving a task to 'In Progress' automatically triggers a signal to the Hermes Agent to begin that task.
- [ ] **Interactive Drag-and-Drop:** Fully implement the `dragstart` and `drop` events in `kanban.js`.

### 🟢 ADVANCED WORKSPACE (Medium Priority)
- [ ] **Editor Persistence:** Add an auto-save feature to the File Editor.
- [ la la **IDE Integration:** Implement the `vscode://` protocol trigger to open the current path in the host's VS Code.

## 🏗️ CURRENT PROGRESS
... (Existing modules: Server, UI Bridge, Basic Workspace, Basic Monitoring) ...
