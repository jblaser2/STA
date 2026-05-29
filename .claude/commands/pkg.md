---
description: Bootstrap a single package workstream (usage: /pkg <name>, e.g. /pkg relion)
---

I want to work on the package: **$ARGUMENTS**

Get me oriented on just this package, then propose the immediate next action. Do this:

1. Find this package's row in `STA/STATUS.md` and report its current state (installed / env /
   data-prep / k=2,3,4 / blockers).
2. Read its instruction guide if one exists (look in `STA/scripts/markdown_instructions/` and the
   package's own dir, e.g. `STA/<pkg>/`).
3. Read any matching memory file in
   `/home/jblaser2/.claude/projects/-home-jblaser2-Research/memory/` (run commands, fixed bugs,
   env name, gotchas).
4. Note the env to use (conda env or MATLAB/IMOD) and confirm it exists.

Then tell me, in a few lines:
- The package's current status.
- The single next concrete action to advance it.
- The exact command(s) to run for that action (with correct env / paths), if known.

Wait for my go-ahead before executing anything that writes files or launches a long job.
Remember: standardized preprocessing (normalize → identical voxel size → identical box size) and
runs at k=2, 3, 4.
