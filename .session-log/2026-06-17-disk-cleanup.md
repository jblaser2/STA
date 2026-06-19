# 2026-06-17 — synthetic_sta disk cleanup

## Goal
`/home` was at 100% (245M free), blocking work. Prune obsolete synthetic
tomograms from `~/Research/synthetic_sta/` (local, not the repo).

## What happened
- Mapped usage (556G total) and cross-checked each dir against STATUS.md before deleting.
- Freed `/home` to **60% used / 354G free** (~357G recovered).
- **Deleted (obsolete, confirmed):**
  - `motor_easy/production/` — old scrapped 3-class set (STATUS: "scrapped/archived")
  - `motor_easy/{run_A,run_B,run_C,test_random,snr_test,subtomos_all,subtomos_proc,subtomos_aln}` — June-1 early runs
  - `motor_easy/{hc_test,hc_test_x10,hc_test_nw}` — ×3/×10/narrow-wedge experiments superseded by `hc_test_x6`
  - `motor_easy/share_professor/` + `professor_demo/` — one-time deliveries (user-confirmed)
  - `nora_test/NorA_0_rec*.mrc` — pipeline-check leftover tomograms
- **Kept:** `motor_easy/hc_test_x6/` (FM_easy canonical), all of `motor_hard/` (active),
  full tomograms in canonical sets (chose NOT to strip ~128G of `tomo_rec*.mrc`).
- ⚠️ **ERROR:** deleted `motor_switch/production_5apix/` — the **canonical** 5 Å/px / 160³ set
  all motor_switch package runs used — wrongly thinking 5 Å/px was off-target (the 13.33
  `production/` was actually the superseded one). 5apix raw subtomos/tomograms GONE, no backup.
  **Regenerable** from `motor_switch/maps/5apix/` + `*_5apix.sh` + `extract_subtomos_5apix.py`/
  `align_all_5apix.py` (all intact); derived results stay committed. Decided to leave it for now.
  Old 13.33 `production/` also deleted (confirmed superseded).
- The permission gate forced explicit naming of each obsolete dir before deletion — that friction
  kept the canonical `hc_test_x6` / `motor_hard` safe; worth keeping for `rm -rf` on data dirs.

## Files changed
- `STATUS.md` — cleanup bullet in Now/Next/Parked + corrected motor_switch / motor_easy Datasets
  entries (deleted paths flagged). Committed `055720c`.
- `motor-switch-dataset-design.md` (memory) — added regeneration recipe + DELETED markers.
- Also committed `c1ee740` (FM_easy cyl mask builder + cyl-test scores) — pre-existing working-tree
  changes the user asked to commit; unrelated to cleanup.

## Where I stopped
Cleanup done, both commits pushed. Repo now shows the OTHER session's live FM_hard work
(staged figures/README/docs + running dynamo-cyl/eman2 experiment) — left untouched per user
("other session should get it").

## Next step
Regenerate `motor_switch/production_5apix/` only if/when motor_switch needs re-running
(recipe in the motor-switch memory). No other follow-up from this session.
