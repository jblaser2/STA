# OPUS-ET T4P Pili Classification — Hand-off Package

Self-contained hand-off for reproducing the **T4P pili subtomogram classification** with
OPUS-ET (opusTomo). For the full method, rationale, and gotchas, read **`T4P/research.md`** —
this file is just the contents index and a starting point.

> This hand-off reflects the current run: **cylindrical r=12 (Y-axis) mask + in-training
> orientation search disabled** (`train_skipalign.py`), giving a **K=2 split of 438 / 234
> (65% / 35%)** at validation SNR² ≈ 3.7. (This supersedes the older threshold-mask result;
> the package-level `README.md` describes that earlier state.)

---

## What's in this package

| Path | Contents |
|------|----------|
| `T4P/research.md` | **Start here.** Complete replication doc: environment, every pipeline step, bugs/gotchas, results, and "What to Share". |
| `T4P/scripts/` | The 10 pipeline scripts (see below). |
| `T4P/output/` | Tier-1 results in opusTomo's native layout (see below). |
| `opusPatches/` | The 2 patched opusTomo source files (`models.py`, `pose.py`) + `README.md` with apply instructions. |

### `T4P/scripts/`
- `runClassification.sh` — master orchestrator (runs Steps 1–7)
- `01_write_star.py` · `02_make_pose.sh` · `03_make_mask.py` · `04_train.sh` ·
  **`train_skipalign.py`** (disables the orientation search — essential) ·
  `05_analyze.sh` · `06_eval_vol.sh` · `07_split_star.sh` · `08_class_averages.py`

### `T4P/output/` (native opusTomo organization)
- `config.pkl`, `split.pkl`, `z.19.pkl` — model config, frozen train/val split, final latents
- `mask.mrc`, `pose_euler.pkl`, `particles.star` — the run inputs
- `split_star/pre0.star`, `pre1.star` — **per-class particle lists** (438 / 234)
- `analyze.19/` — `umap`/`z_pca` embeddings, and `kmeans2/` with:
  - `reference0.mrc`, `reference1.mrc` — **per-class averaged 3D volumes** (open in ChimeraX)
  - `class_averages.png` — **2D class-average projections**
  - `labels.pkl`, `centers*` — cluster assignments and centers

### `opusPatches/`
- `models.py` (Bug 4: CTF-exponent NaN), `pose.py` (Bug 3: single-bin HEALPix), `README.md`

---

## To reproduce

1. **Environment** — build the `opuset` conda env (PyTorch **cu128**, not the bundled
   `environment.yml`). Recipe in `T4P/research.md` → "Environment Setup".
2. **Patched opusTomo** — clone opusTomo, copy `opusPatches/{models.py,pose.py}` into its
   `cryodrgn/`, then `pip install -e .` (see `opusPatches/README.md`).
3. **Input particles** — the 672 subtomograms (`aligned_tom*.mrc`) + `dummy_ctf.star`, which
   are **not included here** (they live in `~/src/particles/`). Place them and point the
   scripts at that directory.
4. **Run** — `bash T4P/scripts/runClassification.sh`, then produce the K=2 result per
   `research.md` → "Iterating on Results".

---

## Not included (needed separately)
- The **patched opusTomo install** (only the 2 patch files are here, in `opusPatches/`).
- The **input particle stack** `~/src/particles/aligned_tom*.mrc` + `dummy_ctf.star`.
- Heavy training artifacts (`weights.*.pkl`, intermediate epochs) — intentionally omitted;
  `weights.19.pkl` can be regenerated or requested if you need to resume / make new volumes.
