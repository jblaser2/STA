---
description: Brief me on current project state so I never start a session cold
---

You are starting a work session on the STA benchmark project. Orient yourself, then give me a
tight briefing. Do this:

1. Read `STA/STATUS.md` (the single source of truth).
2. Read the most recent file in `STA/.session-log/` (highest date in filename).
3. Skim relevant memory in `/home/jblaser2/.claude/projects/-home-jblaser2-Research/memory/` for
   any package named in "Now/Next".

Then print a briefing in exactly this shape, no more than ~12 lines total:

- **Where we are:** 1–2 sentences.
- **Last session:** 1 line (date + what got done, from the session-log).
- **Next step:** the single most important thing to do now (quote it from STATUS.md "Next").
- **Blockers / parked:** 1 line if any.
- **Package matrix snapshot:** one line listing which packages are ✅ done vs 🟡 in progress.

Do NOT start doing the work. Just brief me and wait for my go-ahead. If `$ARGUMENTS` names a
package, focus the briefing on that package's row + memory instead.
