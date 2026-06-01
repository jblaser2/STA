# DISCA — Unsupervised Deep Subtomogram Clustering Runbook

> How to classify the **pre-aligned 3D T4P subtomograms** with DISCA on this machine, and what it
> found. DISCA (Zeng et al., *PNAS* 2023) is a **template-and-label-free, fully unsupervised**
> deep-learning clusterer — methodologically the most independent of the packages we've run (no
> template, no alignment, no reference). Written for the STA benchmark (672 T4P, 80³, 13.328 Å/px).

## 1. Why DISCA fits our data (unlike emClarity / RELION-modern)

DISCA operates **directly on pre-extracted subtomogram volumes** — it learns 3D structural features
with a CNN (the "YOPO" feature model) and clusters them with a GMM, iterating EM-style. It needs **no
tilt series, no tomograms, no CTF model, no initial reference** — exactly our situation. It is the
opposite end of the method spectrum from the template/ML-alignment packages (RELION, PyTom, Protomo),
which makes it a strong independent test of their result.

DISCA also **auto-selects the cluster count** by a distortion-based Davies–Bouldin index (DDBI) over
a list of `candidateKs`. For the benchmark we constrain `candidateKs=[k]` and run k=2/3/4 separately.

## 2. What's installed

| Asset | Path |
|---|---|
| conda env `disca` (python 3.11, torch 2.11.0+cu128) | `~/conda-envs/disca` |
| DISCA run copy (PyTorch) + trimmed util | `~/Research/disca_work/{torch_disca_run.py, util.py}` |
| k=2/3/4 driver | `~/Research/disca_work/run_disca_all.sh` |
| input pickle / labels / models (local, gitignored) | `~/Research/disca_work/{disca_input_672.pickle, model/}` |

### Install recipe
1. `mamba create -n disca python=3.11`
2. `pip install --index-url https://download.pytorch.org/whl/cu128 torch torchvision`
   then `pip install "numpy<2" scikit-learn scipy mrcfile tqdm matplotlib`.
3. Grab the two DISCA PyTorch files from AITom
   (`aitom/classify/deep/unsupervised/disca/{torch_disca.py, util.py}`), then **two source edits**
   the README explicitly anticipates ("modify the lines for importing modules to run independently"):
   - **`util.py`**: comment out the top-level `import keras` / `from tensorflow.keras...` lines
     (3 lines). The PyTorch path never calls util's keras functions — `torch_disca.py` defines its own
     torch versions of `statistical_fitting` / `update_output_layer` / `YOPO_classification`. This
     avoids needing TensorFlow at all.
   - **`torch_disca.py`**: change `from aitom...disca.util import *` → `from util import *`.
4. Stock-script fixes we made in `torch_disca_run.py` (all in the `Config` class + `__main__`):
   - `device = torch.device('cuda:2')` → **`cuda:0`** (the stock value assumes a multi-GPU node; we
     have one RTX 5080).
   - `candidateKs`, `model_path`/`label_path`, and the `__main__` `x_train` path wired to env vars
     (`DISCA_K`, `DISCA_TAG`, `DISCA_OUTDIR`, `DISCA_INPUT`) so k=2/3/4 run without editing the file.

## 3. GPU — works natively on Blackwell (sm_120)

Unlike emClarity (CUDA-10 binaries that only *JIT* onto sm_120), DISCA runs on modern PyTorch, so the
GPU is **natively supported**: `torch 2.11.0+cu128`, `get_arch_list()` includes `sm_120`, device
capability `(12, 0)`, `conv3d` on GPU verified. No JIT, no shim. Each k-run (672 particles, 32³, up to
80 EM iterations × 10 epochs) finishes in ~2 min on the 5080.

## 4. Input data prep

DISCA loads a pickle of the AITom container `{'vs': {key: {'v': <3D array>}}}` and stacks the volumes
into `(n, 1, s, s, s)`. Its YOPO model is trained at the paper's **32³** box, so we downsample our 80³
volumes. **`scripts/data_prep/build_disca_input.py`**:
- Fourier-crops each 80³ → 32³ (anti-aliased; new sampling ~33.3 Å/px — the coarse pattern-mining
  regime DISCA targets).
- Standardises each subtomogram (zero-mean / unit-std).
- Writes `~/Research/disca_work/disca_input_672.pickle` (672 particles; local, gitignored).
Particles are already aligned/centered, so DISCA classifies the **same set** RELION/PyTom/Protomo did.

## 5. Running k = 2 / 3 / 4

```bash
conda activate disca
export DISCA_INPUT=~/Research/disca_work/disca_input_672.pickle
for K in 2 3 4; do
  DISCA_K=$K DISCA_TAG=k$K python ~/Research/disca_work/torch_disca_run.py > log_k$K.txt 2>&1
done       # = scripts/data_prep/run_disca_all.sh
```
Outputs per run: `model/labels_k{K}.pickle` (per-particle cluster label) + `model/model_torch_k{K}.pth`.
**Note:** DISCA saves labels/model **only when its DDBI internal-validity index improves**, so the
saved `labels_k{K}.pickle` is DISCA's *best-validity* solution, not necessarily the last iteration.

## 6. Analysis

**`scripts/analysis/disca_report.py`** maps the saved labels back to particles (same container order),
builds class averages from the **full-resolution 80³ originals**, computes inter-class normalised
cross-correlation, and renders central XY/XZ/YZ slices per class → `disca/results/`
(`RESULTS.md` + PNGs).

## 7. Results (672 T4P particles)

DISCA's **best-DDBI** solution at each k:

| k | class sizes (occupancy) | inter-class CC |
|---|---|---|
| 2 | 634 (94%), 38 (6%) | 0.835 |
| 3 | 630 (94%), 28 (4%), 14 (2%) | 0.550–0.788 |
| 4 | 625 (93%), 20 (3%), 14 (2%), 13 (2%) | 0.567–0.775 |

**Interpretation.** By its **own** internal-validity criterion, DISCA selects **one dominant ~94%
class plus a few small outlier groups** at every k — the *same* structure RELION/PyTom/Protomo found.
The class-average slices confirm it: the dominant class is a **crisp pilus** (periodic filament
subunits in XY, proper missing-wedge smear in XZ/YZ), while the small classes (13–38 particles) are
**noisy small-N averages**, not structurally distinct conformers. The lower inter-class CC vs RELION
(0.97) is driven by that small-N noise in the outlier averages, **not** by genuine structural
difference.

**Honest nuance.** DISCA's *transient* EM iterations did explore **balanced** partitions
(e.g. k=2 → [501, 171], k=3 → [265, 113, 294]) — DISCA's discriminative design resists degenerate
single-cluster solutions during training. But its DDBI model-selection criterion ultimately prefers
the one-dominant-plus-outliers solution, i.e. it does **not** certify a balanced discrete split as the
better clustering.

**Bottom line — these four packages failed to recover the two real classes (corrected 2026-06-01).**
RELION, PyTom, Protomo, **and** DISCA all converged on one-dominant-class-plus-outliers. Initially
read as "no discrete heterogeneity," but **Stefano's expert consult is that this dataset contains two
distinct, obvious pili-phase classes, and Dynamo recovers them well** (`dynamo/`). So the convergent
result is a **shared failure to separate the two known phases**, not a true null — a real and useful
benchmark signal: at our settings these four packages underperform Dynamo on real data with (expert)
ground truth. Possible causes to probe: DISCA's coarse 32³ (~33 Å/px) sampling may wash out the
phase difference; the template/ML-alignment packages may need different masks / lowpass / parameters;
the phase difference may be subtle relative to the missing wedge. The **ETSimulations synthetic sets**
(known ground truth) will pin down "method limitation" vs "parameter choice."

**Caveats.** 32³ downsampling (~33 Å/px) limits DISCA to coarse features — fine (~10 Å) heterogeneity
could be invisible at this sampling; the synthetic benchmark (with a known small-difference class)
will test that. Small outlier classes are DISCA's expected behaviour on a dominant-state-plus-noise
population and are not necessarily distinct states.
