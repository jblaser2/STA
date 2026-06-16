#!/usr/bin/env python3
"""10-slice slab average of a SINGLE subtomo from each class (A, C), vs its central slice."""
import csv, os, numpy as np, mrcfile
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt

OUT = os.path.dirname(os.path.abspath(__file__))
ALN = os.path.expanduser("~/Research/synthetic_sta/motor_easy/production/subtomos/merged_all_aln")
rows = list(csv.DictReader(open(os.path.join(OUT,'pair_labels.csv'))))

pick = {cls: next(r['orig_file'] for r in rows if r['gt_label']==cls) for cls in ('A','C')}

fig, axs = plt.subplots(2,2,figsize=(8,8))
for col,cls in enumerate(('A','C')):
    with mrcfile.open(os.path.join(ALN,pick[cls]), permissive=True) as m:
        v = m.data.astype(np.float32)
    N = v.shape[0]; cz=N//2; lo,hi = cz-5,cz+5
    axs[0,col].imshow(v[cz], cmap='gray')
    axs[0,col].set_title(f"{cls} — {pick[cls]}\ncentral Z (z={cz})", fontsize=10)
    axs[1,col].imshow(v[lo:hi].mean(0), cmap='gray')
    axs[1,col].set_title(f"{cls} — 10-slice slab (z={lo}:{hi})", fontsize=10)
    for r in (0,1): axs[r,col].axis('off')
plt.suptitle("Single subtomo per class — central slice vs 10-slice slab", fontsize=13)
plt.tight_layout()
p = os.path.join(OUT,'single_subtomo_slab_AC.png'); plt.savefig(p, dpi=150); plt.close()
print("picked", pick); print("saved", p)
