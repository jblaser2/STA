#!/usr/bin/env python3
import csv, os, numpy as np
from collections import Counter
from math import comb
from scipy.optimize import linear_sum_assignment
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt

OUT = os.path.dirname(os.path.abspath(__file__))
PAIR = os.path.expanduser("~/Research/STA/packages/dynamo/dynamo_outputs/easy_pair_AC/pair_labels.csv")
gt = {r['orig_file']: r['gt_label'] for r in csv.DictReader(open(PAIR))}

# parse it025 data.star: need rlnImageName + rlnClassNumber columns
star = os.path.join(OUT, "run_it025_data.star")
cols = {}; rows = []; in_p = False; header = True
for line in open(star):
    s = line.strip()
    if s.startswith("data_particles"): in_p = True; continue
    if in_p and s.startswith("_rln"):
        name = s.split()[0][1:]; idx = int(s.split("#")[1]) - 1; cols[name] = idx; continue
    if in_p and s and not s.startswith("_") and not s.startswith("loop_") and not s.startswith("#"):
        rows.append(s.split())
img_i = cols["rlnImageName"]; cls_i = cols["rlnClassNumber"]
y, p = [], []
for r in rows:
    base = os.path.basename(r[img_i])
    if base in gt:
        y.append(gt[base]); p.append(int(float(r[cls_i])))
la = sorted(set(y)); lb = sorted(set(p))
M = np.zeros((len(la), len(lb)), int)
ia = {v:i for i,v in enumerate(la)}; ib = {v:i for i,v in enumerate(lb)}
for a,b in zip(y,p): M[ia[a], ib[b]] += 1
sc=sum(comb(int(v),2) for v in M.sum(0)); sr=sum(comb(int(v),2) for v in M.sum(1))
si=sum(comb(int(v),2) for v in M.flat); n=comb(len(y),2); exp=sr*sc/n; mx=(sr+sc)/2
ari=(si-exp)/(mx-exp) if mx!=exp else 0.0
ri, ci = linear_sum_assignment(-M)
acc = M[ri, ci].sum()/len(y)
col_to_gt = {lb[j]: la[i] for i,j in zip(ri,ci)}
Mo = np.zeros((len(la),len(la)),int)
for a,b in zip(y,p): Mo[ia[a], ia[col_to_gt[b]]] += 1
print(f"N={len(y)} GT={dict(Counter(y))} pred-class={dict(Counter(p))}")
print(f"raw GTxclass {la} cols=class{lb}\n{M}")
print(f"ARI={ari:.3f}  acc={acc:.3f}")

fig,(a0,a1)=plt.subplots(1,2,figsize=(9,4.2))
def draw(ax,Mx,xt,t):
    ax.imshow(Mx,cmap='Greens'); ax.set_xticks(range(len(xt))); ax.set_yticks([0,1])
    ax.set_xticklabels(xt); ax.set_yticklabels([f"GT {l}" for l in la])
    for i in range(Mx.shape[0]):
        for j in range(Mx.shape[1]):
            ax.text(j,i,str(Mx[i,j]),ha='center',va='center',color='white' if Mx[i,j]>Mx.max()/2 else 'black',fontsize=15,fontweight='bold')
    ax.set_title(t,fontsize=10); ax.set_ylabel("ground truth")
draw(a0,M,[f"class{c}" for c in lb],"raw: GT x RELION class")
draw(a1,Mo,[f"pred {l}" for l in la],"optimal 1-to-1")
fig.suptitle(f"RELION Class3D k=2  A vs C (focused diff mask)   ARI={ari:.3f}  acc={acc:.2f}  N={len(y)}",fontsize=12)
plt.tight_layout(); cm=os.path.join(OUT,'confusion_relion_AC_k2_diffmask.png'); plt.savefig(cm,dpi=140); plt.close()
print("saved",cm)
