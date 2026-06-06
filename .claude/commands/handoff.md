---
description: Close out the session — update STATUS.md, write a session-log entry, update memory, stage changes
---

Wrap up this work session so the next one (mine, Eben's, or on my phone) can resume instantly.
Work from what actually happened in THIS conversation — do not invent progress. Steps:

1. **Update `STA/STATUS.md`:**
   - Update the "Last updated" date to today.
   - Refresh "Now / Next / Parked".
   - Update any package-matrix cells whose state changed this session (✅/🟡/⬜, notes, blockers).
   - Add/adjust "Open Decisions" if new ones surfaced.

1a. **Sync package READMEs** (required if any package result changed in step 1):
   - Update `packages/README.md` — the progress matrix row(s) for changed package(s).
   - Update `packages/<pkg>/README.md` — the results table and next steps section.
   - This keeps the package-level docs in sync with STATUS.md (see CLAUDE.md §"Package README Protocol").

2. **Write a session-log entry** at `STA/.session-log/YYYY-MM-DD-<short-topic>.md` (today's date)
   with sections: Goal / What happened / Files changed / Where I stopped / Next step.
   If a file for today+topic already exists, append to it rather than overwriting.

3. **Update memory** in `/home/jblaser2/.claude/projects/-home-jblaser2-Research/memory/` only for
   *durable* knowledge gained (install quirks, fixed bugs, working commands). Keep *status* in
   STATUS.md, not memory. Update `MEMORY.md` index if you added a file.

4. **Stage** the changed repo files with `git add` (do NOT commit or push unless I explicitly ask).
   Then show me `git status` and a one-paragraph summary of what you changed.

Be concise. The point is a clean, accurate handoff, not prose.
