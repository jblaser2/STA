# 2026-05-29 — Cross-session workflow setup

**Goal:** Stop starting every Claude session cold. Build a project-state system, tighten Claude
Code config, and set up phone supervision of the campus node.

**What happened:**
- Reviewed all 11 prior sessions + repo + memory. Root problem: no single project-status view and
  no session-handoff convention, so each session re-derived state.
- Created `STATUS.md` (package matrix + Now/Next/Parked + open decisions) as the single source of truth.
- Created this `.session-log/` convention.
- Added slash commands `/status`, `/handoff`, `/pkg` under `STA/.claude/commands/`.
- Added shared permission allowlist `STA/.claude/settings.json`.
- Restructured `STA/CLAUDE.md` and `~/Research/CLAUDE.md` (filled compute specs + remote note).
- Memory hygiene: status moved out of memory files into `STATUS.md`.
- Remote: installed `tmux` (conda env `tools`), wrote `~/.tmux.conf`.

**Files changed:** `STATUS.md`, `.session-log/`, `.claude/commands/*`, `.claude/settings.json`,
`CLAUDE.md` (both), memory files, `~/.tmux.conf`.

**Where I stopped:** Workflow scaffolding in place and staged.

**Next step:** Start using the loop — `/status` at session start, `/handoff` at end. First real
workstream to resume: PyTom identical-averages blocker (see STATUS.md), or ETSimulations
production synthetic data.
