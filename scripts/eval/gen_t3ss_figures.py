#!/usr/bin/env python3
"""Generate T3SS Injectisome figures for packages/README.md.

Produces:
  packages/figures/T3SS/header_maps_and_avgs.png   — source maps + GT subtomo avgs
  packages/figures/T3SS/mask_overlay.png           — global average with mask contour
  packages/figures/T3SS/perfect_confusion.png      — 2×2 diagonal (signal only)
  packages/figures/T3SS/<pkg>_class_avgs.png       — per-package cluster averages
  outputs/T3SS/<pkg>/confusion_<pkg>_t3ss.png      — per-package confusion (all GT rows)

Dataset: 415 particles — class_B 215 (IM ring + sorting platform) +
         class_C 120 (IM ring absent) + junk 80. Box 48³, 13.33 Å/px.
ARI scored on signal particles only (class_B + class_C, excluding junk).

Run with eman2 env from STA repo root:
  conda run -n eman2 python3 scripts/eval/gen_t3ss_figures.py
"""
import os, csv, numpy as np, mrcfile
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from collections import Counter
from sklearn.metrics import adjusted_rand_score, confusion_matrix
from scipy.optimize import linear_sum_assignment

STA    = "/home/jblaser2/Research/STA"
STDIR  = "/home/jblaser2/Research/synthetic_sta/injectisome/subtomos/merged_BC_t3ss"
MAPS   = "/home/jblaser2/Research/synthetic_sta/injectisome/maps"
AVGS   = "/home/jblaser2/Research/synthetic_sta/injectisome/subtomos"
FIGDIR = os.path.join(STA, "packages/figures/T3SS")
os.makedirs(FIGDIR, exist_ok=True)

GT_SIGNAL = ["class_B", "class_C"]   # scoring classes
GT_ALL    = ["class_B", "class_C", "junk"]
GT_COUNTS = {"class_B": 215, "class_C": 120}

# ------------------------------------------------------------------ helpers --

def load(path):
    with mrcfile.open(path, permissive=True) as f:
        return f.data.astype(np.float32)

def crop_to_particle_box(vol):
    """Crop 96³ source map/average to the 48³ particle box used in classification.
    Two-step crop applied during dataset construction:
      step 1 (crop_subtomos.py):   [:, 48:, 32:]  → (96, 48, 64)
      step 2 (reshape_to_48.py):   [23:71, :, 1:49] → (48, 48, 48)
    Combined: vol[23:71, 48:96, 33:81]
    """
    return vol[23:71, 48:96, 33:81]

def cslice(vol):
    return vol[vol.shape[0] // 2]

def norm(img):
    lo, hi = np.percentile(img, 2), np.percentile(img, 98)
    return np.clip((img - lo) / max(hi - lo, 1e-6), 0, 1)

def show(ax, img, title, fontsize=10, title_color="black"):
    ax.imshow(norm(img), cmap="gray", vmin=0, vmax=1)
    ax.set_title(title, fontsize=fontsize, color=title_color)
    ax.axis("off")

# Cache subtomo slices
_cache = {}
def get_slice(fn):
    if fn not in _cache:
        _cache[fn] = cslice(load(os.path.join(STDIR, fn)))
    return _cache[fn]

# GT map (all 415 particles: B, C, junk)
gt_map = {r["file"]: r["label"]
          for r in csv.DictReader(open(os.path.join(STDIR, "labels.csv")))}

def load_pred(path):
    return {r["file"]: r["pred_label"]
            for r in csv.DictReader(open(path))}

def signal_ari(gt_list, pred_list):
    """ARI computed on signal-only particles (class_B and class_C)."""
    pairs = [(g, p) for g, p in zip(gt_list, pred_list) if g in GT_SIGNAL]
    if not pairs:
        return float("nan")
    gs, ps = zip(*pairs)
    return adjusted_rand_score(list(gs), list(ps))

def hungarian_accuracy(gt_list, pred_list):
    gt_u = sorted(set(gt_list))
    pr_u = sorted(set(pred_list))
    gt_idx = np.array([gt_u.index(g) for g in gt_list])
    pr_idx = np.array([pr_u.index(p) for p in pred_list])
    cm = confusion_matrix(gt_idx, pr_idx, labels=range(len(gt_u)))
    n = max(len(gt_u), len(pr_u))
    pad = np.zeros((n, n), dtype=float)
    pad[:cm.shape[0], :cm.shape[1]] = cm
    ri, ci = linear_sum_assignment(-pad)
    acc = pad[ri, ci].sum() / len(gt_list)
    return acc, cm, gt_u, pr_u

# -------------------------------------------------------- header figure ------

def gen_header():
    fig, axes = plt.subplots(1, 4, figsize=(14, 3.8))
    panels = [
        (cslice(crop_to_particle_box(load(f"{MAPS}/class_B_t3ss.mrc"))), "Class B — source map\n(IM ring + sorting platform)"),
        (cslice(crop_to_particle_box(load(f"{MAPS}/class_C_t3ss.mrc"))), "Class C — source map\n(IM ring absent)"),
        (cslice(crop_to_particle_box(load(f"{AVGS}/avg_class_B.mrc"))),  "Class B — subtomo avg\n(215 particles)"),
        (cslice(crop_to_particle_box(load(f"{AVGS}/avg_class_C.mrc"))),  "Class C — subtomo avg\n(120 particles)"),
    ]
    for ax, (img, title) in zip(axes, panels):
        show(ax, img, title, fontsize=10)
    plt.tight_layout()
    out = f"{FIGDIR}/header_maps_and_avgs.png"
    plt.savefig(out, dpi=120, bbox_inches="tight"); plt.close()
    print(f"  wrote {out}")

# -------------------------------------------------------- mask overlay -------

def gen_mask_overlay():
    # Global average of all 415 subtomograms
    all_files = [f for f in gt_map]
    global_avg = np.mean([cslice(load(os.path.join(STDIR, f))) for f in all_files], axis=0)

    mask_vol = load(f"{MAPS}/mask_t3ss.mrc")
    mask_slice = mask_vol[mask_vol.shape[0] // 2]

    fig, axes = plt.subplots(1, 2, figsize=(9, 4.2))

    # Left: global average alone
    axes[0].imshow(norm(global_avg), cmap="gray", vmin=0, vmax=1)
    axes[0].set_title("Global average (415p)", fontsize=11)
    axes[0].axis("off")

    # Right: global average + mask contour
    axes[1].imshow(norm(global_avg), cmap="gray", vmin=0, vmax=1)
    axes[1].contour(mask_slice, levels=[0.5], colors="red", linewidths=1.5)
    axes[1].set_title("Classification mask (cylinder, red contour)", fontsize=11)
    axes[1].axis("off")

    plt.suptitle("T3SS Injectisome — 48³ box, 13.33 Å/px", fontsize=12, y=1.02)
    plt.tight_layout()
    out = f"{FIGDIR}/mask_overlay.png"
    plt.savefig(out, dpi=130, bbox_inches="tight"); plt.close()
    print(f"  wrote {out}")

# -------------------------------------------------------- perfect confusion --

def gen_perfect_confusion():
    labels = ["class_B\n(IM ring +\nsorting platform)", "class_C\n(IM ring\nabsent)"]
    counts = [215, 120]
    n = 2
    cm = np.diag(counts).astype(float)
    cm_norm = cm / np.array(counts)[:, None]

    fig, ax = plt.subplots(figsize=(4.0, 3.6))
    im = ax.imshow(cm_norm, vmin=0, vmax=1, cmap="Blues")
    ax.set_xticks(range(n)); ax.set_xticklabels(labels, fontsize=9)
    ax.set_yticks(range(n)); ax.set_yticklabels(labels, fontsize=9)
    ax.set_xlabel("Predicted cluster", fontsize=9)
    ax.set_ylabel("GT class", fontsize=9)
    ax.set_title("Perfect classification\nT3SS k=2  (signal ARI = 1.0)", fontsize=10,
                 fontweight="bold")
    for i in range(n):
        for j in range(n):
            pct = cm_norm[i, j]
            color = "white" if pct > 0.55 else "black"
            ax.text(j, i, f"{int(cm[i, j])}\n({pct:.0%})",
                    ha="center", va="center", fontsize=9, color=color, fontweight="bold")
    fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04, label="Recall")
    plt.tight_layout()
    out = f"{FIGDIR}/perfect_confusion.png"
    plt.savefig(out, dpi=150, bbox_inches="tight"); plt.close()
    print(f"  wrote {out}")

# ------------------------------------------------- per-package figures ------

def gen_pkg_figures(pkg, pred_path, outdir, k_label):
    if not os.path.exists(pred_path):
        print(f"  SKIP {pkg}: {pred_path} not found"); return None

    pred = load_pred(pred_path)
    shared = sorted(set(gt_map) & set(pred))
    if not shared:
        print(f"  SKIP {pkg}: no overlapping keys"); return None

    gt_list   = [gt_map[f] for f in shared]
    pred_list = [pred[f]   for f in shared]

    ari = signal_ari(gt_list, pred_list)
    acc, cm, gt_u, pr_u = hungarian_accuracy(gt_list, pred_list)

    # Cluster groups sorted by size descending
    groups = {}
    for f in shared:
        groups.setdefault(pred[f], []).append(f)
    clabels = sorted(groups, key=lambda k: -len(groups[k]))
    n_cls = len(clabels)

    # --- class average panel ---
    fig, axes = plt.subplots(1, n_cls, figsize=(3.2 * n_cls, 3.6))
    if n_cls == 1: axes = [axes]
    fig.patch.set_facecolor("black")
    for ax, cl in zip(axes, clabels):
        files = groups[cl]
        avg = np.mean([get_slice(f) for f in files], axis=0)
        maj_gt, maj_n = Counter(gt_map[f] for f in files).most_common(1)[0]
        ax.imshow(norm(avg), cmap="gray", vmin=0, vmax=1)
        ax.set_title(f"n={len(files)}\n(mostly {maj_gt}: {maj_n}/{len(files)})",
                     color="white", fontsize=9)
        ax.axis("off")
        for sp in ax.spines.values():
            sp.set_edgecolor("white"); sp.set_linewidth(0.5)
    fig.suptitle(f"{pkg}  {k_label}  signal ARI={ari:.3f}",
                 color="white", fontsize=10, y=1.01)
    avg_out = f"{FIGDIR}/{pkg}_class_avgs.png"
    plt.savefig(avg_out, dpi=120, bbox_inches="tight",
                facecolor="black", pad_inches=0.04)
    plt.close()
    print(f"  class avgs → {avg_out}")

    # --- confusion matrix (all GT rows: B, C, junk) ---
    os.makedirs(outdir, exist_ok=True)
    n_gt = len(gt_u); n_pr = len(pr_u)
    fig2, ax2 = plt.subplots(figsize=(max(4, n_pr + 1), max(3.5, n_gt + 0.5)))
    im2 = ax2.imshow(cm, cmap="Blues")
    ax2.set_xticks(range(n_pr)); ax2.set_xticklabels([str(p) for p in pr_u], fontsize=10)
    ax2.set_yticks(range(n_gt)); ax2.set_yticklabels([str(g) for g in gt_u], fontsize=10)
    ax2.set_xlabel("Predicted", fontsize=11)
    ax2.set_ylabel("Ground Truth", fontsize=11)
    ax2.set_title(f"{pkg}  T3SS  {k_label}\nsignal ARI={ari:.3f}  Acc={acc:.3f}", fontsize=11)
    plt.colorbar(im2, ax=ax2)
    for i in range(n_gt):
        for j in range(n_pr):
            ax2.text(j, i, int(cm[i, j]), ha="center", va="center", fontsize=10,
                     color="white" if cm[i, j] > cm.max() / 2 else "black")
    plt.tight_layout()
    cm_out = f"{outdir}/confusion_{pkg}_t3ss.png"
    plt.savefig(cm_out, dpi=130, bbox_inches="tight"); plt.close()
    print(f"  confusion    → {cm_out}")

    split = "/".join(str(len(groups[c])) for c in clabels)
    print(f"  {pkg}: signal ARI={ari:.3f}  Acc={acc:.3f}  split={split}")
    return {"pkg": pkg, "k": k_label, "ari": ari, "acc": acc, "split": split,
            "avg_png": avg_out, "cm_png": cm_out}

# ------------------------------------------------------------------ main ----

# Use best k per package (k=3 for those where it helps, else k=2)
PKGS = [
    ("disca",    f"{STA}/outputs/T3SS/disca/disca_t3ss_k3.csv",              f"{STA}/outputs/T3SS/disca",    "k=3"),
    ("peet",     f"{STA}/outputs/T3SS/peet/predictions_k3_pc1_10.csv",       f"{STA}/outputs/T3SS/peet",     "k=3 pc1_10"),
    ("opus",     f"{STA}/outputs/T3SS/opus/opus_t3ss_k3.csv",                f"{STA}/outputs/T3SS/opus",     "k=3"),
    ("stopgap",  f"{STA}/outputs/T3SS/stopgap/stopgap_t3ss_k3.csv",          f"{STA}/outputs/T3SS/stopgap",  "k=3"),
    ("pytom",    f"{STA}/outputs/T3SS/pytom/pytom_t3ss_k3.csv",              f"{STA}/outputs/T3SS/pytom",    "k=3"),
    ("relion",   f"{STA}/outputs/T3SS/relion/relion_t3ss_k3.csv",            f"{STA}/outputs/T3SS/relion",   "k=3"),
    ("protomo",  f"{STA}/outputs/T3SS/protomo/protomo_t3ss_k2.csv",          f"{STA}/outputs/T3SS/protomo",  "k=2"),
    ("dynamo",   f"{STA}/outputs/T3SS/dynamo/dynamo_t3ss_k2.csv",            f"{STA}/outputs/T3SS/dynamo",   "k=2"),
    ("tomoflow", f"{STA}/outputs/T3SS/tomoflow/tomoflow_t3ss_k2.csv",        f"{STA}/outputs/T3SS/tomoflow", "k=2"),
    # EMAN2: no prediction CSV — omit from figures
]

if __name__ == "__main__":
    print("=== T3SS Injectisome figure generation ===")

    print("\n[1/4] Header maps + GT averages")
    gen_header()

    print("\n[2/4] Mask overlay (global average + mask contour)")
    gen_mask_overlay()

    print("\n[3/4] Perfect confusion matrix")
    gen_perfect_confusion()

    print("\n[4/4] Per-package class averages + confusion matrices")
    results = []
    for pkg, pred_path, outdir, k_label in PKGS:
        print(f"\n--- {pkg} ({k_label}) ---")
        r = gen_pkg_figures(pkg, pred_path, outdir, k_label)
        if r:
            results.append(r)

    print("\n=== Summary ===")
    for r in results:
        print(f"| {r['pkg']:10s} | {r['k']:12s} | signal ARI={r['ari']:.3f}  Acc={r['acc']:.3f} | split {r['split']} |")
    print("Done.")
