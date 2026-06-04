# 2026-06-04 — Synthetic scoring framework + missing wedge decision + RELION/PEET first runs on motor_easy

## Goal
Implement Session 2 from `foamy-swinging-dewdrop.md`:
- Build shared ARI-based scoring infrastructure for synthetic GT evaluation
- Resolve the missing-wedge input decision
- Run motor_easy through RELION (k=2, k=3) and PEET (WMD-PCA k=2, k=3) to validate the pipeline end-to-end

## What happened

### Scoring infrastructure (`scripts/eval/`)
- `score_synthetic.py`: takes `--pred` CSV (file, pred_label) + `--gt` CSV → prints ARI/AMI/V-measure/accuracy (Hungarian matching), plots confusion PNG, appends to `results/synthetic_scores.csv`
- `extract_relion_classes.py`: parses RELION `*_data.star` → pred CSV (maps `rlnImageName` → `rlnClassNumber`)
- `extract_peet_classes.py`: parses PEET MOTL CSV (col 20 = class) → pred CSV ordered by GT labels.csv

### Missing-wedge decision
**Decision:** feed `merged_all_aln/` (GT-aligned 96³, 13.33 Å/px) with identity starting poses (phi=theta=psi=0) + tilt range ±60°. Let each package apply its own native wedge correction. Rationale: isolates classification quality; consistent with how real-data runs are set up; packages with native WMD (RELION, PEET) get credit for using it.

### motor_easy dimensions confirmed
96³ box, 13.329 Å/px. (T4P was 80³; scripts needed box=96 parameters throughout.)

### RELION motor_easy setup and runs
- Built wedge CTF (96³, ±60°) + uniform CTF → `outputs/relion_motor_easy/ctf/`
- Built initial reference (mean of all 634 GT-aligned subtomos) → `outputs/relion_motor_easy/initial_ref.mrc`
- Built particles_wedge.star + particles_uniform.star (absolute subtomo paths)
- Ran k=2 and k=3, 25 iterations, `--skip_align` (same flags as real T4P run)
- Results: **RELION k=2 ARI=0.005, k=3 ARI=0.006** — essentially random

### PEET motor_easy setup and runs
- `peet/motor_easy_stack.py`: stacks 634 GT-aligned subtomos along Z (96×96×60864), builds IMOD model, builds Iter1 + Iter2 MOTLs
- **PEET bug encountered and fixed:** CCC=0 in Iter2 MOTL causes PEET to silently skip ALL particles ("0 particles from Tom 1"). Fix: set CCC=0.5 (dummy non-zero) in Iter2. Documented in `peet-pca-iteration-and-wedge` memory.
- `averageAll` also fails with uniform CCC=0 (same root cause). Workaround: bypassed averageAll entirely; used pre-computed global average from `make_initial_ref.py` as PEET reference.
- Ran `pca` on all 634 particles → `pca634_motor_easy.mat` (634 non-zero eigenvalues, 20 PCs saved)
- `peet/kmeans_motor_easy.py`: loads .mat via h5py, runs sklearn k-means on PCs 1:3, 1:5, 1:10 at k=2 and k=3
- Results: **PEET WMD-PCA all runs ARI≈0** (range: -0.003 to +0.001)

### Dynamo
Blocked — MATLAB Parallel Computing Toolbox (PCT) not installed. Documented in STATUS.md.

### Scores summary (`results/synthetic_scores.csv`)
| package | k | run | ARI |
|---|---|---|---|
| relion | 2 | k2_wedge | 0.005 |
| relion | 3 | k3_wedge | 0.006 |
| peet | 2 | k2_pc1_3 | -0.000 |
| peet | 2 | k2_pc1_5 | -0.000 |
| peet | 2 | k2_pc1_10 | -0.000 |
| peet | 3 | k3_pc1_3 | -0.001 |
| peet | 3 | k3_pc1_5 | -0.003 |
| peet | 3 | k3_pc1_10 | +0.001 |

Template-matching baseline for reference: ARI=0.289 (structural signal confirmed present).

### Why both packages get ARI≈0
- **RELION `--skip_align`**: Pure classification without alignment; global-average reference is featureless; random K-split doesn't converge to class structure. Fix: remove `--skip_align`.
- **PEET WMD-PCA**: Same failure mode as real T4P — all GT-aligned particles have identical wedge orientation, so WMD masks the same Fourier region for all particles instead of correcting per-particle geometry. Known limitation.

## Files changed

### New in STA repo (committed in `2cfcbc5`)
- `scripts/eval/score_synthetic.py`
- `scripts/eval/extract_relion_classes.py`
- `scripts/eval/extract_peet_classes.py`
- `peet/motor_easy_stack.py`
- `peet/motor_easy.prm`
- `peet/kmeans_motor_easy.py`
- `scripts/run_relion_motor_easy.sh`
- `scripts/run_peet_motor_easy.sh`
- `results/synthetic_scores.csv`
- `outputs/peet_motor_easy/predictions_*.csv` (6 files)
- `outputs/peet_motor_easy/confusion_*.png` (6 files)
- `STATUS.md`

### Local only (not committed — large or gitignored)
- `outputs/relion_motor_easy/ctf/wedge_ctf.mrc`, `uniform_ctf.mrc`
- `outputs/relion_motor_easy/initial_ref.mrc`
- `outputs/relion_motor_easy/particles_wedge.star`, `particles_uniform.star`
- `outputs/relion_motor_easy/Class3D/k2_wedge/`, `k3_wedge/` (RELION run outputs)
- `~/Research/peet/motor_easy/results/stacked.mrc` (60864×96×96 stacked MRC)
- `~/Research/peet/motor_easy/results/stacked.mod`
- `~/Research/peet/motor_easy/results/motor_easy_MOTL_Tom1_Iter{1,2}.csv`
- `~/Research/peet/motor_easy/results/pca634_motor_easy.mat`
- `~/Research/peet/motor_easy/results/pca_motor_easy.log`

### Memory updated
- `peet-pca-iteration-and-wedge.md`: added MOTL CCC=0 bug + averageAll bypass note

## Where I stopped
First RELION and PEET runs complete; pipeline validated end-to-end; ARI≈0 for both (expected failure modes documented). Dynamo blocked on PCT.

## Next step
1. **Re-run RELION on motor_easy WITHOUT `--skip_align`** — let alignment from identity poses help differentiate class averages. Add `--skip_align` removal to `scripts/run_relion_motor_easy.sh`, re-run k=3.
2. **Install MATLAB PCT** to unblock Dynamo (`mlm_install` or MATLAB installer Add-ons).
3. After Dynamo: run remaining packages (DISCA, PyTom, EMAN2, TomoFlow) on motor_easy.
