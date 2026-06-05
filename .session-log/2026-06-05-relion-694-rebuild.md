# Session: RELION 694-particle rebuild (2026-06-05)

## What happened

Continued from previous session. `align_all_classes.py` had been launched in background to rebuild
`merged_all_aln/` with all 694 particles. Script completed while context was compacted.

### Verified output
- `merged_all_aln/`: 694 subtomograms (subtomo_0000.mrc … subtomo_0693.mrc) + labels.csv
- Class counts: A=246, B=271, C=177 = 694 total

### Rebuilt RELION inputs (all 694 particles)
- `outputs/relion_motor_easy/particles_wedge.star` — 694 entries, absolute paths to merged_all_aln/
- `outputs/relion_motor_easy/initial_ref.mrc` — global average of 694 subtomos
- `avg_class{A,B,C}_aligned.mrc` at `~/Research/synthetic_sta/motor_easy/production/subtomos/` — per-class GT averages

### RELION rerun (v3 config: GT-seeded + firstiter_cc + skip_align)
Config unchanged from v3: K=3, tau2_fudge=8, ini_high=60, solvent_mask (r=32 Y-10), skip_align,
firstiter_cc, no --norm --scale, --j 8 --gpu "". Output: `outputs/relion_motor_easy/Class3D/k3_wedge_v3_694/`

Results:
- **iter 1 (firstiter_cc = CC assignment): ARI=0.380, Acc=74.4%** ← best
- iter 2 (likelihood EM kicks in): ARI=0.099, Acc=54.9% ← collapse continues

Improvement over 634-particle run (iter1 ARI=0.254) likely due to 60 extra class-B particles.
Pattern unchanged: firstiter_cc gives good separation, subsequent likelihood iterations collapse
due to insufficient per-particle SNR.

### Scoring fix
`build_relion_star.py` writes absolute paths for subtomo images; the STAR→CSV parser in this
session used `#N` column indices (not loop order) to correctly extract `_rlnClassNumber`. Old
parser erroneously read CTF column as class label.

Appended 2 rows to `results/synthetic_scores.csv`:
- `relion,motor_easy,3,k3_wedge_v3_694_iter1,694,0.380,0.324,0.326,0.744,...`
- `relion,motor_easy,3,k3_wedge_v3_694_iter2,694,0.099,0.097,0.099,0.549,...`

`outputs/relion_motor_easy/Class3D/k3_wedge_v3_694/predictions.csv` = iter1 (canonical best).

## Next
1. **PEET motor_easy on 694 particles** — rerun k-means on new `merged_all_aln/` labels.csv
2. **Dynamo motor_easy** — PCT confirmed installed; proceed with MRA on 694-particle set
3. emClarity synthetic-only track
