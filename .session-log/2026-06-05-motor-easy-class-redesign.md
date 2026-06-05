# Session: motor_easy class C redesign (2026-06-05)

## Goal
Finalize motor_easy synthetic dataset class definitions. PEET and RELION both scored ARI≈0 for
class C confusion (B vs C were too similar under nested A⊃B⊃C design).

## What happened

### Root cause analysis
Old design: A⊃B⊃C nested — C_core = B minus rod/hook (smallest structural diff, L2=0.340).
RELION and PEET systematically merged B and C. Identified the nested structure as the core problem.

### Class C redesigned → C_noRodHook = C-ring only
Old C (C_core): MS-ring + P-ring + L-ring, y=46–63 base px (removed C-ring AND rod/hook)
New C (C_noRodHook): C-ring ONLY, CUT2_C=46.5 base px (removes everything above membrane neck)

Intermediate step: CUT2_C=54 (removed L-ring/outer membrane ring visible in slice view).
Final step: CUT2_C=46.5 (cut 8 more output voxels off top = removes MS-ring too).

### Final pairwise L2 diffs (CUT2_C=46.5)
- A vs B: 0.431 (unchanged — different from before)
- A vs C_noRodHook: 0.387 (was 0.333 for C_core)
- B vs C_noRodHook: 0.696 (was 0.340 for C_core — **2× improvement**)
- Min pair: A vs C = 0.387

### Biological story (finalized)
- A = full motor (C-ring + MS-ring + P/L-rings + rod/hook)
- B = motor without C-ring (periplasmic/extracellular assembly)
- C = C-ring only (isolated cytoplasmic switch complex)
Three maximally distinct assembly-intermediate classes.

## Files changed
- `~/Research/synthetic_sta/motor_easy/make_variants.py` — CUT2_C 54→46.5, updated docstring
- `~/Research/synthetic_sta/motor_easy/maps/class_C_noRodHook.mrc` — regenerated (local only)
- `outputs/relion_motor_easy/B_vs_Cnew_comparison.png` — 3-class comparison figure (staged)

## Where I stopped
New class maps generated and verified. **Simulated particles for class C have NOT been regenerated.**
Current `merged_all_aln/` still uses old C_core definition (177 particles). All prior RELION/PEET
scores in `results/synthetic_scores.csv` used the old C definition — still valid as archived results
for the old design, but the "production" dataset needs a full re-simulation of class C.

## Next step
1. Re-simulate class C using new C_noRodHook map:
   - Edit `~/Research/synthetic_sta/motor_easy/run_classC.sh` to use `class_C_noRodHook.mrc`
   - Run ~5-6 ETSim batches (≈177 particles, ~6 min each)
2. Rebuild `merged_all_aln/` (A=246, B=271, C_new=177)
3. Rebuild RELION/PEET inputs and rerun packages
4. Dynamo motor_easy (PCT confirmed installed — ready to go)
5. emClarity synthetic-only track
