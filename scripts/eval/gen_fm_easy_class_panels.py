#!/usr/bin/env python3
"""Generate FM_easy (2-class hc) figures for packages/README.md:
  1. header_maps_and_avgs.png  — source density maps (A,C) + GT subtomo averages (A,C)
  2. <pkg>_class_avgs.png       — per-package class averages (mean of subtomos per predicted
                                  cluster), central slice. Computed from each package's pred CSV.
All panels use the central axis-0 (Z) slice, which shows the A (full motor) vs C (truncated
base) axial-extent difference most clearly. Run with relion-5.0 env.
"""
import os, csv, numpy as np, mrcfile
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt

STA = "/home/jblaser2/Research/STA"
ALN = "/home/jblaser2/Research/synthetic_sta/motor_easy/hc_test_x6/subtomos/merged_AC_full"
MAPS = "/home/jblaser2/Research/synthetic_sta/motor_easy/hc_test_x6/maps"
FIGDIR = os.path.join(STA, "packages/figures/FM_easy")
os.makedirs(FIGDIR, exist_ok=True)

def load(p):
    return mrcfile.open(p, permissive=True).data.astype(np.float32)

def cslice(vol):
    return vol[vol.shape[0] // 2]          # central axis-0 (Z) slice

def show(ax, img, title):
    lo, hi = np.percentile(img, [2, 98])
    ax.imshow(img, cmap="gray", vmin=lo, vmax=hi)
    ax.set_title(title, fontsize=11); ax.axis("off")

# GT labels for each particle (for majority annotation of package clusters)
gt = {r["file"]: r["label"] for r in csv.DictReader(open(os.path.join(ALN, "labels.csv")))}

# ---- 1. Header: source maps + GT averages ----
panels = [
    (cslice(load(f"{MAPS}/class_A_full.mrc")),       "Class A — source map\n(mature full motor)"),
    (cslice(load(f"{MAPS}/class_C_noRodHook.mrc")),  "Class C — source map\n(early cytoplasmic base)"),
    (cslice(load(f"{STA}/outputs/FM_easy/relion/ref_classA_hc.mrc")), "Class A — subtomo avg\n(271 particles)"),
    (cslice(load(f"{STA}/outputs/FM_easy/relion/ref_classC_hc.mrc")), "Class C — subtomo avg\n(271 particles)"),
]
fig, ax = plt.subplots(1, 4, figsize=(13, 3.6))
for a, (im, t) in zip(ax, panels): show(a, im, t)
plt.tight_layout(); plt.savefig(f"{FIGDIR}/header_maps_and_avgs.png", dpi=120, bbox_inches="tight"); plt.close()
print("wrote header_maps_and_avgs.png")

# ---- 2. Per-package class averages from predictions ----
# (pkg key, pred CSV) — all have columns file,pred_label
PKGS = [
    ("peet",     "outputs/FM_easy/peet/predictions_k2_pc1_10.csv"),
    ("disca",    "outputs/FM_easy/disca/disca_motor_easy_k2.csv"),
    ("dynamo",   "outputs/FM_easy/dynamo/dynamo_motor_easy_k2.csv"),
    ("tomoflow", "outputs/FM_easy/tomoflow/tomoflow_motor_easy_k2.csv"),
    ("pytom",    "outputs/FM_easy/pytom/pytom_motor_easy_k2.csv"),
    ("protomo",  "outputs/FM_easy/protomo/protomo_motor_easy_k2.csv"),
    ("eman2",    "outputs/FM_easy/eman2/eman2_motor_easy_k2.csv"),
    ("opus",     "outputs/FM_easy/opus/opus_motor_easy_k2.csv"),
    ("relion",   "outputs/FM_easy/relion/run_k2_blind/pred_blind.csv"),
]
# cache subtomo slices once
cache = {}
def get_slice(fn):
    if fn not in cache:
        cache[fn] = cslice(load(os.path.join(ALN, fn)))
    return cache[fn]

for pkg, predrel in PKGS:
    pred = list(csv.DictReader(open(os.path.join(STA, predrel))))
    groups = {}
    for r in pred:
        groups.setdefault(r["pred_label"], []).append(r["file"])
    labels = sorted(groups, key=lambda k: -len(groups[k]))   # largest cluster first
    fig, ax = plt.subplots(1, len(labels), figsize=(3.2 * len(labels), 3.4))
    if len(labels) == 1: ax = [ax]
    for a, lab in zip(ax, labels):
        files = groups[lab]
        avg = np.mean([get_slice(f) for f in files], axis=0)
        # majority GT class in this cluster
        from collections import Counter
        maj = Counter(gt[f] for f in files).most_common(1)[0]
        show(a, avg, f"cluster {lab}: n={len(files)}\n(mostly GT {maj[0]}: {maj[1]}/{len(files)})")
    plt.tight_layout(); plt.savefig(f"{FIGDIR}/{pkg}_class_avgs.png", dpi=120, bbox_inches="tight"); plt.close()
    print(f"wrote {pkg}_class_avgs.png  ({'/'.join(str(len(groups[l])) for l in labels)})")
