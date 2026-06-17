#!/usr/bin/env python3
"""Perfect (ARI=1.0) 2-class confusion matrix for FM_easy (A=271, C=271). relion-5.0 env."""
import numpy as np, matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from pathlib import Path

GT = {"A\n(full motor)": 271, "C\n(base only)": 271}
labels = list(GT); counts = list(GT.values()); n = len(labels)
cm = np.diag(counts).astype(float); cmn = cm / np.array(counts)[:, None]
fig, ax = plt.subplots(figsize=(3.0, 2.8)); im = ax.imshow(cmn, vmin=0, vmax=1, cmap="Blues")
ax.set_xticks(range(n)); ax.set_xticklabels(labels, fontsize=9)
ax.set_yticks(range(n)); ax.set_yticklabels(labels, fontsize=9)
ax.set_xlabel("Predicted cluster", fontsize=9); ax.set_ylabel("GT class", fontsize=9)
ax.set_title("Perfect classification\nFM_easy 2-class (ARI = 1.0)", fontsize=10, fontweight="bold")
for i in range(n):
    for j in range(n):
        ax.text(j, i, f"{int(cm[i,j])}\n({cmn[i,j]:.0%})", ha="center", va="center",
                fontsize=9, color="white" if cmn[i, j] > 0.55 else "black", fontweight="bold")
fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04, label="Recall")
plt.tight_layout()
out = Path("packages/figures/FM_easy/perfect_confusion.png"); out.parent.mkdir(parents=True, exist_ok=True)
plt.savefig(out, dpi=150, bbox_inches="tight"); print("Saved:", out)
