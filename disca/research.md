# DISCA — How It Works and How We Use It

**Method:** DISCA = *Deep Iterative Subtomogram Clustering Approach*
**Paper:** Zeng, Kahng, Xue, Mahamid, Chang, Xu, "High-throughput cryo-ET structural pattern mining
by unsupervised deep iterative subtomogram clustering," *PNAS* 120(15):e2213149120 (2023).
**Source:** AITom — `xulabs/aitom`, module `aitom/classify/deep/unsupervised/disca/`
**Install on this machine:** conda env `disca` (python 3.11, torch 2.11.0+cu128); run copy in
`~/Research/disca_work/`.

DISCA is a **template-free and label-free, fully unsupervised** deep-learning method that discovers
subsets of structurally homogeneous subtomograms by *learning* 3D features and modeling their
distribution — no reference, no alignment, no CTF model, and (critically for us) **no tilt series**.
It therefore operates **directly on pre-extracted, pre-aligned subtomogram volumes**, which is exactly
the form of our real T4P data. This makes it the most methodologically independent classifier in the
STA benchmark relative to the template/ML-alignment packages (RELION, PyTom, Protomo, Dynamo, PEET).

---

## 1. The algorithm

DISCA runs a **generalized EM loop** that alternates between learning features and re-clustering,
re-training the network on its own evolving cluster assignments:

1. **Feature extraction — the "YOPO" model.** A 3D CNN (`YOPOFeatureModel` in `torch_disca.py`)
   maps each subtomogram to a 1024-D feature vector. It is a multi-scale, densely-connected stack of
   ten 3D-conv blocks whose channel outputs (64,80,96,…,208) are concatenated to 1360 channels, batch-
   normalised, then linearly projected to 1024. Because the blocks pool spatially, the feature is
   essentially channel-wise, so the model is input-size tolerant (we still use the paper's 32³ box).
2. **Statistical fitting (clustering).** A Gaussian Mixture Model is fit on the PCA-reduced features
   for each candidate cluster count `k` in `candidateKs`. DISCA selects `k` by a **distortion-based
   Davies–Bouldin index (DDBI)** — a cluster-validity score (lower = better separated / more compact).
3. **Cluster matching.** Across iterations the new labels are matched to the previous ones by the
   Hungarian algorithm (so cluster identities stay stable), and empty clusters are removed.
4. **Convergence check.** If labels stop changing (within tolerance over `M` iterations) the loop ends.
5. **Supervised fine-tuning.** Treating the current cluster labels as (smoothed) targets, the CNN is
   trained for a few epochs with a multi-margin loss, sharpening the features. Then back to step 1.
6. **Model selection.** Whenever the DDBI **improves**, the current labels and network are saved. The
   final saved `labels_k{K}.pickle` is therefore DISCA's **best-validity** solution, not necessarily
   the last iteration's.

Key consequence for benchmarking: DISCA both **learns its own features** and **chooses (or scores)
the cluster number** — it is not just k-means on fixed descriptors. Its discriminative training tends
to resist degenerate single-cluster solutions, so during iteration it explores fairly balanced
partitions; the DDBI criterion then decides which partition is actually best-supported.

---

## 2. Installation (RHEL 10, RTX 5080)

```bash
mamba create -n disca python=3.11
conda activate disca
pip install --index-url https://download.pytorch.org/whl/cu128 torch torchvision
pip install "numpy<2" scikit-learn scipy mrcfile tqdm matplotlib
```

Get the two PyTorch DISCA files from AITom
(`aitom/classify/deep/unsupervised/disca/{torch_disca.py, util.py}`) and apply the two import edits
the project README explicitly invites ("modify the lines for importing modules to run independently"):

- **`util.py`** — comment out the three top-level `import keras` / `from tensorflow.keras…` lines.
  The PyTorch path never calls util's keras functions (`torch_disca.py` defines its own torch versions
  of `statistical_fitting` / `update_output_layer` / `YOPO_classification`), so TensorFlow is not
  needed at all.
- **`torch_disca.py`** — change `from aitom…disca.util import *` → `from util import *`.

Two stock-script bugs/assumptions we fixed in our run copy (`~/Research/disca_work/torch_disca_run.py`):

- `Config.device` was hard-coded `cuda:2` (a multi-GPU node assumption) → **`cuda:0`** (single RTX 5080).
- `Config.candidateKs`, the model/label output paths, and the `__main__` input path were wired to
  environment variables (`DISCA_K`, `DISCA_TAG`, `DISCA_OUTDIR`, `DISCA_INPUT`) so k=2/3/4 run without
  editing the file.

**GPU note.** Unlike emClarity (CUDA-10 binaries that merely JIT onto Blackwell), DISCA runs on modern
PyTorch, which supports **sm_120 natively** — `torch.cuda.get_arch_list()` includes `sm_120`, device
capability `(12,0)`, GPU `conv3d` verified. Each k-run (672 particles, 32³, up to 80 EM iterations)
finishes in ~2 minutes.

---

## 3. Input data format

DISCA loads a single pickle holding the AITom subtomogram container:

```python
{'vs': { <key>: {'v': <3D numpy array>, 'm': None, 'id': <key>}, ... }}
```

The `'v'` volumes are stacked into a tensor of shape `(n, 1, s, s, s)`. The YOPO model is trained at
the paper's **32³** box, so we downsample our 80³ / 13.328 Å-px volumes.

**`scripts/data_prep/build_disca_input.py`** (run in the `disca` env):
- Fourier-crops each 80³ → 32³ (anti-aliased; new sampling ≈ 33.3 Å/px — the coarse pattern-mining
  regime DISCA was designed for),
- standardises each subtomogram to zero-mean / unit-std,
- writes `~/Research/disca_work/disca_input_672.pickle` (672 particles; local, gitignored).

The particles are already aligned and centered, so DISCA classifies the **same set** RELION / PyTom /
Protomo / Dynamo did.

---

## 4. Running k = 2 / 3 / 4

```bash
conda activate disca
export DISCA_INPUT=~/Research/disca_work/disca_input_672.pickle
for K in 2 3 4; do
  DISCA_K=$K DISCA_TAG=k$K python ~/Research/disca_work/torch_disca_run.py > log_k$K.txt 2>&1
done
```

This is wrapped in **`scripts/data_prep/run_disca_all.sh`**. Each run writes
`model/labels_k{K}.pickle` (one cluster label per particle, in input-container order) and
`model/model_torch_k{K}.pth`. To let DISCA pick `k` itself instead of fixing it, set
`DISCA_K=2,3,4` (or one large `k` that over-partitions) and read the `Estimated K` it reports.

---

## 5. Analysis

**`scripts/analysis/disca_report.py`** maps the saved labels back to particles, builds class averages
from the **full-resolution 80³ originals** (DISCA itself worked on 32³ copies), computes inter-class
normalised cross-correlation, and renders central XY/XZ/YZ slices per class plus a compact
side-by-side comparison → **`disca/results/`** (`RESULTS.md` + PNGs, committed). Large runtime
artifacts (input pickle, models, label pickles, run copies of the AITom scripts) stay in
`~/Research/disca_work/` (local, outside the repo).

---

## 6. Results on T4P (672 particles) and interpretation

DISCA's best-DDBI solution at each k (full table + figures in `disca/results/`):

| k | class sizes (occupancy) | inter-class CC |
|---|---|---|
| 2 | 634 (94%), 38 (6%) | 0.835 |
| 3 | 630 (94%), 28 (4%), 14 (2%) | 0.550–0.788 |
| 4 | 625 (93%), 20 (3%), 14 (2%), 13 (2%) | 0.567–0.775 |

At every k DISCA's own validity criterion prefers **one dominant ~94% class plus a few small outlier
groups**. The slice figures show the dominant class is a **crisp pilus** (periodic filament subunits
in XY, missing-wedge smear in XZ/YZ) while the small (13–38-particle) classes are **noisy small-N
averages** — which is what depresses the inter-class CC, not genuine structural difference.

### Important correction (Stefano consult, 2026-06-01)
This dataset **does** contain **two distinct, obvious pili-phase classes**, and **Dynamo separates
them well** (`dynamo/`). So DISCA's one-dominant-class result — shared by RELION, PyTom, and Protomo —
is a **failure to recover the two known phases**, *not* evidence that no heterogeneity exists. That is
a legitimate and informative benchmark outcome: at the settings we used, these four packages
underperform Dynamo on real data with expert ground truth.

Hypotheses for the failure, to test next:
- **Sampling:** DISCA's 32³ / ~33 Å-px downsampling may wash out the phase difference. Re-run at a
  larger box (e.g. 64³) — the YOPO model tolerates it — to see whether the two phases separate.
- **Coarse vs subtle signal:** the phase difference may be small relative to the missing-wedge
  artefact; mask/lowpass choices in the alignment-based packages likely matter.
- **Ground-truth anchor:** the **ETSimulations** synthetic datasets (known classes) will distinguish
  a true method limitation from a parameter choice and calibrate each package's sensitivity.

---

## 7. Files

| File | Purpose |
|---|---|
| `scripts/data_prep/build_disca_input.py` | 80³→32³ Fourier-crop into the DISCA pickle |
| `scripts/data_prep/run_disca_all.sh` | k=2/3/4 driver (env-driven `Config`) |
| `scripts/analysis/disca_report.py` | class averages, CC, slice + side-by-side figures |
| `scripts/markdown_instructions/DISCA.md` | the short benchmark runbook (this doc is the fuller version) |
| `disca/results/` | `RESULTS.md` + class-average PNGs |
| `~/Research/disca_work/` | run copies of `torch_disca_run.py` + trimmed `util.py`, input pickle, models (local) |
