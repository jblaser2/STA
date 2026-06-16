#!/usr/bin/env python3
"""
QC: average the FM_easy (motor_easy) input subtomos globally and per GT class,
then render the central Z slice of each side by side.

Run: conda run -n relion-5.0 python3 scripts/eval/qc_motor_easy_class_avgs.py
"""
import os, csv
import numpy as np
import mrcfile
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

SUB = ("/home/jblaser2/Research/synthetic_sta/motor_easy/production/"
       "subtomos/merged_all_aln")
OUT = "/home/jblaser2/Research/STA/outputs/FM_easy/input_qc"
os.makedirs(OUT, exist_ok=True)

# --- read labels ---
rows = []
with open(os.path.join(SUB, "labels.csv")) as f:
    for r in csv.DictReader(f):
        rows.append((r["file"], r["label"]))
classes = sorted({lab for _, lab in rows})
print(f"{len(rows)} particles, classes={classes}")

# --- accumulate sums ---
def load(fn):
    with mrcfile.open(os.path.join(SUB, fn), permissive=True) as m:
        return np.asarray(m.data, dtype=np.float32)

shape = load(rows[0][0]).shape
apix = None
with mrcfile.open(os.path.join(SUB, rows[0][0]), permissive=True) as m:
    apix = float(m.voxel_size.x)
print(f"box={shape}  apix={apix:.3f} A")

sums = {c: np.zeros(shape, np.float64) for c in classes}
counts = {c: 0 for c in classes}
gsum = np.zeros(shape, np.float64)
for fn, lab in rows:
    v = load(fn)
    sums[lab] += v
    counts[lab] += 1
    gsum += v
gavg = (gsum / len(rows)).astype(np.float32)
cavg = {c: (sums[c] / counts[c]).astype(np.float32) for c in classes}

# --- save averages as MRC ---
def save_mrc(arr, name):
    p = os.path.join(OUT, name)
    with mrcfile.new(p, overwrite=True) as m:
        m.set_data(arr.astype(np.float32))
        m.voxel_size = apix
    return p

save_mrc(gavg, "avg_ALL_694.mrc")
for c in classes:
    save_mrc(cavg[c], f"avg_class_{c}_{counts[c]}.mrc")

# --- montage of central Z slices ---
panels = [("ALL (694)", gavg)] + [(f"{c} ({counts[c]})", cavg[c]) for c in classes]
zc = shape[0] // 2
# common intensity scaling across all panels (per-panel robust percentiles of the
# global avg so contrast is comparable)
fig, axes = plt.subplots(1, len(panels), figsize=(4 * len(panels), 4.4))
for ax, (title, vol) in zip(axes, panels):
    sl = vol[zc]
    vmin, vmax = np.percentile(sl, [2, 98])
    ax.imshow(sl, cmap="gray", vmin=vmin, vmax=vmax, origin="lower")
    ax.set_title(f"{title}\ncentral Z (z={zc})", fontsize=11)
    ax.axis("off")
fig.suptitle(f"FM_easy input class averages — central Z slice  "
             f"(box {shape[0]}³, {apix:.2f} Å/px)", fontsize=13)
fig.tight_layout(rect=[0, 0, 1, 0.94])
montage = os.path.join(OUT, "motor_easy_input_class_avgs_centralZ.png")
fig.savefig(montage, dpi=130)
print("saved:", montage)
for c in classes:
    print(f"  class {c}: {counts[c]} particles -> avg_class_{c}_{counts[c]}.mrc")
