#!/usr/bin/env python3
import csv, os, numpy as np, mrcfile
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from collections import Counter
from math import comb

OUT = os.path.dirname(os.path.abspath(__file__))
lab = {int(r['tag']): r['gt_label'] for r in csv.DictReader(open(os.path.join(OUT,'pair_labels.csv')))}
fmap = {int(r['tag']): r['orig_file'] for r in csv.DictReader(open(os.path.join(OUT,'pair_labels.csv')))}
pred = {int(r['tag']): int(r['pred_label']) for r in csv.DictReader(open(os.path.join(OUT,'predictions_k2.csv')))}
tags = sorted(lab); y = [lab[t] for t in tags]; p = [pred[t] for t in tags]
la = sorted(set(y)); lb = sorted(set(p))

# raw GT x predicted-cluster confusion (honest; no degenerate collapse)
M = np.zeros((len(la), len(lb)), int)
ia = {v:i for i,v in enumerate(la)}; ib = {v:i for i,v in enumerate(lb)}
for a,b in zip(y,p): M[ia[a], ib[b]] += 1
# OPTIMAL 1-to-1 cluster->GT assignment (Hungarian) for a labeled 2x2
from scipy.optimize import linear_sum_assignment
ri, ci = linear_sum_assignment(-M)            # maximize diagonal
col_to_gt = {lb[j]: la[i] for i, j in zip(ri, ci)}
pred_gt = [col_to_gt[v] for v in p]
Mo = np.zeros((len(la), len(la)), int)
for a,b in zip(y, pred_gt): Mo[ia[a], ia[b]] += 1

sc=sum(comb(int(v),2) for v in M.sum(0)); sr=sum(comb(int(v),2) for v in M.sum(1))
si=sum(comb(int(v),2) for v in M.flat); n=comb(len(y),2)
exp=sr*sc/n; mx=(sr+sc)/2
ari=(si-exp)/(mx-exp) if mx!=exp else 0.0
acc=sum(int(a==b) for a,b in zip(y,pred_gt))/len(y)

with open(os.path.join(OUT,'score.txt'),'w') as f:
    f.write(f"N={len(y)} GT={dict(Counter(y))} pred={dict(Counter(p))}\n")
    f.write(f"raw confusion rows=GT{la} cols=pred{lb}\n{M}\n")
    f.write(f"oriented rows=GT cols=pred-mapped {la}\n{Mo}\n")
    f.write(f"ARI={ari:.3f} best-match-acc={acc:.3f}\n")
print(open(os.path.join(OUT,'score.txt')).read())

# ---- confusion matrix figure: raw GT x cluster (left) + optimal-assigned (right) ----
fig, (ax0, ax1) = plt.subplots(1, 2, figsize=(9,4.2))
def draw(ax, Mx, xt, title):
    ax.imshow(Mx, cmap='Blues')
    ax.set_xticks([0,1]); ax.set_yticks([0,1])
    ax.set_xticklabels(xt); ax.set_yticklabels([f"GT {l}" for l in la])
    for i in range(2):
        for j in range(2):
            ax.text(j,i,str(Mx[i,j]),ha='center',va='center',
                    color='white' if Mx[i,j]>Mx.max()/2 else 'black',fontsize=16,fontweight='bold')
    ax.set_title(title, fontsize=10); ax.set_ylabel("ground truth")
draw(ax0, M, [f"cluster {c}" for c in lb], "raw: GT x k-means cluster")
draw(ax1, Mo, [f"pred {l}" for l in la], "optimal 1-to-1 cluster->label")
fig.suptitle(f"Dynamo dpkpca k=2  A vs C   ARI={ari:.3f}   acc={acc:.2f}   N={len(y)}", fontsize=12)
plt.tight_layout(); cm=os.path.join(OUT,'confusion_AC_k2.png'); plt.savefig(cm,dpi=140); plt.close()
print("saved",cm)

# ---- central slices of a few subtomos (3 A + 3 C) ----
ALN = os.path.expanduser("~/Research/synthetic_sta/motor_easy/production/subtomos/merged_all_aln")
picks=[]
for cls in ('A','C'):
    ts=[t for t in tags if lab[t]==cls][:3]
    picks += [(cls,t) for t in ts]
fig, axs = plt.subplots(2,3,figsize=(9,6))
for ax,(cls,t) in zip(axs.flat, picks):
    with mrcfile.open(os.path.join(ALN, fmap[t]), permissive=True) as m:
        v=m.data.astype(np.float32)
    cz=v.shape[0]//2
    ax.imshow(v[cz],cmap='gray'); ax.set_title(f"{cls}  tag{t}  pred{pred[t]}",fontsize=10)
    ax.axis('off')
plt.suptitle("Central-Z slices — raw GT-aligned subtomos (A top, C bottom)")
plt.tight_layout(); sl=os.path.join(OUT,'sample_slices_AC.png'); plt.savefig(sl,dpi=140); plt.close()
print("saved",sl)
