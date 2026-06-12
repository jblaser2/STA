#!/usr/bin/env python3
"""
sweep_dynamo_motor_switch.py — nc-sweep k-means on Dynamo dpkpca eigencomponents
for motor_switch, mirroring the motor_easy protocol (best nc found by sweep, not
the fixed nc=10 in the .m driver).

Reads eigencomponents.mat (E: N_particles x n_components, rows in GT order
subtomo_0000..N-1), sweeps nc = 2..NC_MAX, runs k-means k=2 at each nc, and
reports ARI vs the 3-label GT (ccw/cw/junk). Writes the best predictions CSV
in the canonical file,pred_label format for score_synthetic.py.

Usage (run from repo root):
  conda run -n relion-5.0 python3 \
    packages/dynamo/FM_switch/scripts/sweep_dynamo_motor_switch.py
"""
import os
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.io import loadmat
from sklearn.cluster import KMeans
from sklearn.metrics import adjusted_rand_score

REPO = Path(__file__).resolve().parents[4]
OUTDIR = REPO / "packages/dynamo/dynamo_outputs/motor_switch_pca"
EIG_MAT = OUTDIR / "eigencomponents.mat"
GT = Path.home() / ("Research/synthetic_sta/motor_switch/"
                    "production_5apix/subtomos/all_particles_aligned/labels.csv")
NC_MAX = 50
K = 2
SEED = 42


def main():
    E = loadmat(EIG_MAT)["E"]
    E = np.asarray(E, dtype=np.float64)
    N, ncomp = E.shape
    print(f"eigencomponents: {N} particles x {ncomp} components")

    gt = pd.read_csv(GT)
    gt["file"] = gt["file"].apply(os.path.basename)
    gt = gt.set_index("file")["label"]
    files = [f"subtomo_{i:04d}.mrc" for i in range(N)]
    gt_labels = gt.loc[files].values
    assert len(gt_labels) == N

    best = dict(ari=-2, nc=None, km=None)
    rows = []
    for nc in range(2, min(NC_MAX, ncomp) + 1):
        km = KMeans(n_clusters=K, n_init=20, max_iter=500,
                    random_state=SEED).fit_predict(E[:, :nc])
        ari = adjusted_rand_score(gt_labels, km)
        rows.append((nc, ari))
        if ari > best["ari"]:
            best.update(ari=ari, nc=nc, km=km)

    print("\nnc sweep (ARI vs ccw/cw/junk GT):")
    for nc, ari in rows:
        mark = "  <-- best" if nc == best["nc"] else ""
        print(f"  nc={nc:2d}: ARI={ari:+.4f}{mark}")

    km = best["km"]
    sizes = np.bincount(km)
    print(f"\nBEST nc={best['nc']}  ARI={best['ari']:+.4f}  sizes={sizes.tolist()}")

    out = OUTDIR / "predictions_k2.csv"
    pd.DataFrame({"file": files, "pred_label": km + 1}).to_csv(out, index=False)
    print(f"wrote {out}  (best nc={best['nc']})")
    print(f"\nScore with:\n  conda run -n relion-5.0 python3 scripts/eval/score_synthetic.py "
          f"--pred {out.relative_to(REPO)} --gt {GT} "
          f"--package dynamo --k 2 --dataset motor_switch "
          f"--run k2_pca_nc{best['nc']}_motor_switch "
          f"--notes 'dpkpca nc-sweep best'")


if __name__ == "__main__":
    main()
