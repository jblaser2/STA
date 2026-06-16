#!/usr/bin/env python3
"""Central-Z slice + 10-slice slab average of the A and C class averages (raw aligned subtomos)."""
import csv, os, numpy as np, mrcfile
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt

OUT = os.path.dirname(os.path.abspath(__file__))
ALN = os.path.expanduser("~/Research/synthetic_sta/motor_easy/production/subtomos/merged_all_aln")
rows = list(csv.DictReader(open(os.path.join(OUT,'pair_labels.csv'))))

avg = {}
for cls in ('A','C'):
    fs = [r['orig_file'] for r in rows if r['gt_label']==cls]
    acc = None
    for f in fs:
        with mrcfile.open(os.path.join(ALN,f), permissive=True) as m:
            v = m.data.astype(np.float32)
        acc = v if acc is None else acc + v
    avg[cls] = acc/len(fs)
    print(f"class {cls}: {len(fs)} particles averaged, box {avg[cls].shape}")

N = avg['A'].shape[0]; cz = N//2
lo, hi = cz-5, cz+5   # 10-slice slab around center

fig, axs = plt.subplots(2,2,figsize=(8,8))
for col,cls in enumerate(('A','C')):
    central = avg[cls][cz]
    slab = avg[cls][lo:hi].mean(0)
    axs[0,col].imshow(central, cmap='gray')
    axs[0,col].set_title(f"class {cls} avg — central Z (z={cz})", fontsize=11)
    axs[1,col].imshow(slab, cmap='gray')
    axs[1,col].set_title(f"class {cls} avg — 10-slice slab (z={lo}:{hi})", fontsize=11)
    for r in (0,1): axs[r,col].axis('off')
plt.suptitle("A vs C class averages (raw GT-aligned subtomos)", fontsize=13)
plt.tight_layout()
p = os.path.join(OUT,'class_avg_AC_slices.png'); plt.savefig(p, dpi=150); plt.close()
print("saved", p)
