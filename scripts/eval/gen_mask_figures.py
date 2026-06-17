#!/usr/bin/env python3
"""Generate per-dataset mask figures for the READMEs: the classification mask (red contour)
overlaid on the dataset's average, in 3 orthogonal central slices. Run with relion-5.0 env."""
import os, numpy as np, mrcfile
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt

STA = "/home/jblaser2/Research/STA"
FIG = os.path.join(STA, "packages/figures")

def load(p): return mrcfile.open(p, permissive=True).data.astype(np.float32)

def panel(avg_path, mask_path, out, title):
    avg = load(avg_path); mask = load(mask_path)
    assert avg.shape == mask.shape, f"{avg.shape} vs {mask.shape}"
    c = [s // 2 for s in avg.shape]
    planes = [("XY (central Z)", avg[c[0]], mask[c[0]]),
              ("XZ (central Y)", avg[:, c[1], :], mask[:, c[1], :]),
              ("YZ (central X)", avg[:, :, c[2]], mask[:, :, c[2]])]
    fig, ax = plt.subplots(1, 3, figsize=(10, 3.6))
    for a, (t, im, mk) in zip(ax, planes):
        lo, hi = np.percentile(im, [2, 98])
        a.imshow(im, cmap="gray", vmin=lo, vmax=hi)
        a.contour(mk, levels=[0.5], colors="red", linewidths=1.6)
        a.set_title(t, fontsize=10); a.axis("off")
    fig.suptitle(title, fontsize=12, fontweight="bold", y=1.02)
    plt.tight_layout(); plt.savefig(out, dpi=120, bbox_inches="tight"); plt.close()
    print("wrote", out)

# T4P: cylindrical mask v2 over the global masked average (80^3)
panel(f"{STA}/data/masked_average/masked_average.mrc",
      f"{STA}/data/T4P_mask/cylindrical_mask_v2.mrc",
      f"{FIG}/T4P/mask_overlay.png",
      "T4P classification mask — cylindrical v2 (r=13, h_pos=0, h_neg=25) on global average")

# FM_easy: A-vs-C diff sphere over the global average (96^3)
panel(f"{STA}/outputs/FM_easy/relion/initial_ref.mrc",
      f"{STA}/packages/dynamo/dynamo_outputs/easy_pair_AC_hc/diff_sphere_r23_y55.mrc",
      f"{FIG}/FM_easy/mask_overlay.png",
      "FM_easy classification mask — A-vs-C diff sphere (r=23, Y-shift) on global average")
