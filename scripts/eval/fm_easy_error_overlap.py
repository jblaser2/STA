#!/usr/bin/env python3
"""Do the FM_easy blind packages misclassify the SAME subtomos?
For each of the 9 blind packages: best-permutation map (Hungarian) predicted clusters -> GT,
mark per-particle miss. Then:
  - per-particle miss-count across packages
  - pairwise Jaccard overlap of error sets (heatmap)  -> figures/FM_easy/error_overlap_jaccard.png
  - top-5 most-missed subtomos: each = average of its 10 central Z-slices, one PNG each
    -> figures/FM_easy/missed_top{1..5}.png
Run with relion-5.0 env.
"""
import os, csv, numpy as np, mrcfile
from scipy.optimize import linear_sum_assignment
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt

STA = "/home/jblaser2/Research/STA"
ALN = "/home/jblaser2/Research/synthetic_sta/motor_easy/hc_test_x6/subtomos/merged_AC_full"
FIG = os.path.join(STA, "packages/figures/FM_easy")
os.makedirs(FIG, exist_ok=True)

PKGS = [
    ("PEET",     "outputs/FM_easy/peet/predictions_k2_pc1_10.csv"),
    ("DISCA",    "outputs/FM_easy/disca/disca_motor_easy_k2.csv"),
    ("Dynamo",   "outputs/FM_easy/dynamo/dynamo_motor_easy_k2.csv"),
    ("TomoFlow", "outputs/FM_easy/tomoflow/tomoflow_motor_easy_k2.csv"),
    ("PyTom",    "outputs/FM_easy/pytom/pytom_motor_easy_k2.csv"),
    ("ProTomo",  "outputs/FM_easy/protomo/protomo_motor_easy_k2.csv"),
    ("EMAN2",    "outputs/FM_easy/eman2/eman2_motor_easy_k2.csv"),
    ("OPUS",     "outputs/FM_easy/opus/opus_motor_easy_k2.csv"),
    ("RELION",   "outputs/FM_easy/relion/run_k2_blind/pred_blind.csv"),
]

gt = {r["file"]: r["label"] for r in csv.DictReader(open(os.path.join(ALN, "labels.csv")))}
files = sorted(gt)
gcls = sorted(set(gt.values()))                       # ['A','C']
gidx = np.array([gcls.index(gt[f]) for f in files])

miss = {}    # pkg -> bool array (True = misclassified)
for name, rel in PKGS:
    pm = {r["file"]: r["pred_label"] for r in csv.DictReader(open(os.path.join(STA, rel)))}
    pcls = sorted(set(pm.values()))
    pidx = np.array([pcls.index(pm[f]) for f in files])
    # Hungarian best-permutation mapping pred-cluster -> GT class
    K = max(len(gcls), len(pcls))
    M = np.zeros((K, K), int)
    for g, p in zip(gidx, pidx):
        M[g, p] += 1
    r, c = linear_sum_assignment(-M)
    pred2gt = {cc: rr for rr, cc in zip(r, c)}
    mapped = np.array([pred2gt.get(p, -1) for p in pidx])
    miss[name] = mapped != gidx
    print(f"{name:9s} acc={1-miss[name].mean():.3f}  misses={miss[name].sum()}")

names = [n for n, _ in PKGS]
missmat = np.vstack([miss[n] for n in names])          # (9, 542)
miss_count = missmat.sum(0)                            # per particle

print("\n--- miss-count distribution (how many of 9 pkgs miss each particle) ---")
for k in range(len(names) + 1):
    n = int((miss_count == k).sum())
    if n: print(f"  missed by {k}/9 pkgs: {n} particles")

# recovering subset (real split) vs collapsed
recov = ["PEET", "DISCA", "Dynamo"]
rc = np.vstack([miss[n] for n in recov]).sum(0)
print(f"\nAmong the 3 recovering pkgs (PEET/DISCA/Dynamo): "
      f"{(rc==3).sum()} particles missed by ALL 3, {(rc==0).sum()} correct in all 3")

# pairwise Jaccard of error sets
J = np.zeros((len(names), len(names)))
for i in range(len(names)):
    for j in range(len(names)):
        a, b = miss[names[i]], miss[names[j]]
        u = (a | b).sum()
        J[i, j] = (a & b).sum() / u if u else 0.0
fig, ax = plt.subplots(figsize=(6.5, 5.5))
im = ax.imshow(J, cmap="viridis", vmin=0, vmax=1)
ax.set_xticks(range(len(names))); ax.set_xticklabels(names, rotation=45, ha="right", fontsize=9)
ax.set_yticks(range(len(names))); ax.set_yticklabels(names, fontsize=9)
ax.set_title("FM_easy: do packages miss the SAME subtomos?\nJaccard overlap of misclassified-particle sets", fontsize=11)
for i in range(len(names)):
    for j in range(len(names)):
        ax.text(j, i, f"{J[i,j]:.2f}", ha="center", va="center",
                color="white" if J[i, j] < 0.6 else "black", fontsize=7)
fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04, label="Jaccard (|∩| / |∪|)")
plt.tight_layout(); plt.savefig(f"{FIG}/error_overlap_jaccard.png", dpi=130, bbox_inches="tight"); plt.close()
print("wrote error_overlap_jaccard.png")

# random-overlap baseline (expected Jaccard if errors independent), for the recovering trio
print("\n--- expected vs observed pairwise Jaccard (recovering trio) ---")
for i in range(len(recov)):
    for j in range(i+1, len(recov)):
        a, b = miss[recov[i]], miss[recov[j]]
        pa, pb = a.mean(), b.mean()
        exp = (pa*pb) / (pa+pb-pa*pb)        # expected Jaccard if independent
        obs = (a&b).sum()/((a|b).sum() or 1)
        print(f"  {recov[i]}–{recov[j]}: observed {obs:.3f}  vs independent {exp:.3f}")

# --- top-5 most-missed subtomos: avg of central 10 Z-slices ---
order = np.argsort(-miss_count)
# break ties by also being missed by the recovering trio (genuinely hard)
top = sorted(range(len(files)), key=lambda i: (-miss_count[i], -rc[i]))[:5]
print("\n--- top-5 most-missed subtomos ---")
for rank, i in enumerate(top, 1):
    f = files[i]
    vol = mrcfile.open(os.path.join(ALN, f), permissive=True).data.astype(np.float32)
    z = vol.shape[0] // 2
    proj = vol[z-5:z+5].mean(0)               # average of 10 central Z-slices
    fig, ax = plt.subplots(figsize=(3.0, 3.2))
    lo, hi = np.percentile(proj, [2, 98])
    ax.imshow(proj, cmap="gray", vmin=lo, vmax=hi); ax.axis("off")
    ax.set_title(f"#{rank} most-missed: {f}\nGT {gt[f]} — missed by {miss_count[i]}/9 pkgs",
                 fontsize=9)
    plt.tight_layout(); plt.savefig(f"{FIG}/missed_top{rank}.png", dpi=130, bbox_inches="tight"); plt.close()
    print(f"  #{rank} {f}  GT={gt[f]}  missed_by={miss_count[i]}/9  (recov trio missed {rc[i]}/3)")
print("wrote missed_top1..5.png")
