#!/usr/bin/env python3
"""
Test whether a DIFFERENCE mask (voxels where two class averages differ) recovers
the per-particle signal that the full-motor mask buries. Builds the mask from
|avg_c1 - avg_c2|, re-runs blind masked PCA+k-means, compares to the full mask.

NOTE: the diff mask is GT-derived (uses labels) -> it measures the achievable
ceiling of mask focusing, not blind discovery.

Run: conda run -n relion-5.0 python3 scripts/eval/diffmask_test_motor_easy.py
"""
import os, csv, itertools
import numpy as np, mrcfile
from scipy.ndimage import gaussian_filter, binary_dilation
from sklearn.decomposition import PCA
from sklearn.cluster import KMeans
from sklearn.metrics import adjusted_rand_score as ARI
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt

SUB  = "/home/jblaser2/Research/synthetic_sta/motor_easy/production/subtomos/merged_all_aln"
QC   = "/home/jblaser2/Research/STA/outputs/FM_easy/input_qc"
fullmask = np.asarray(mrcfile.open(os.path.join(QC, "motor_easy_mask.mrc"), permissive=True).data, np.float32)
avg = {c: np.asarray(mrcfile.open(os.path.join(QC, f), permissive=True).data, np.float32)
       for c, f in [("A","avg_class_A_246.mrc"),("B","avg_class_B_271.mrc"),("C","avg_class_C_177.mrc")]}
rows = [(r["file"], r["label"]) for r in csv.DictReader(open(os.path.join(SUB, "labels.csv")))]

VOLC = {}
def vol(fn):
    if fn not in VOLC:
        VOLC[fn] = gaussian_filter(np.asarray(mrcfile.open(os.path.join(SUB,fn),permissive=True).data,np.float32),1.5)
    return VOLC[fn]

def diff_mask(c1, c2, keep_frac=0.05, edge=3):
    d = gaussian_filter(np.abs(avg[c1]-avg[c2]), 2.0) * (fullmask>0.05)
    thr = np.percentile(d[d>0], 100*(1-keep_frac/ (np.mean(fullmask>0.05))))  # ~keep_frac of box
    core = d >= thr
    core = binary_dilation(core, iterations=2)
    # soft cosine edge via distance
    from scipy.ndimage import distance_transform_edt
    dist = distance_transform_edt(~core)
    m = np.clip(1 - dist/edge, 0, 1).astype(np.float32)
    return m

def blind_ari(idx, files, y, normalize):
    X=[]
    for f,_ in files:
        x=vol(f)[idx]
        if normalize: x=(x-x.mean())/(x.std()+1e-6)
        X.append(x)
    X=np.stack(X); X=X-X.mean(0)
    Z=PCA(20,svd_solver="randomized",random_state=0).fit_transform(X)
    km=KMeans(2,n_init=20,random_state=0).fit(Z).labels_
    return ARI(y,km)

pairs=[("A","B"),("B","C"),("A","C")]
print(f"full mask: {(fullmask>0.05).sum()} vox ({100*(fullmask>0.05).mean():.1f}% box)\n")
print(f"{'pair':5s} {'mask':10s} {'vox':>7s} {'%box':>6s}  {'ARI raw':>8s} {'ARI norm':>9s}")
masks_for_fig={}
for c1,c2 in pairs:
    files=[(f,l) for f,l in rows if l in (c1,c2)]
    y=np.array([0 if l==c1 else 1 for _,l in files])
    fidx=fullmask>0.05
    print(f"{c1}-{c2}  {'full':10s} {fidx.sum():7d} {100*fidx.mean():5.1f}  "
          f"{blind_ari(fidx,files,y,False):8.3f} {blind_ari(fidx,files,y,True):9.3f}")
    dm=diff_mask(c1,c2); didx=dm>0.05; masks_for_fig[(c1,c2)]=dm
    with mrcfile.new(os.path.join(QC,f"diffmask_{c1}{c2}.mrc"),overwrite=True) as o:
        o.set_data(dm); o.voxel_size=13.329
    print(f"{'':5s} {'diff':10s} {didx.sum():7d} {100*didx.mean():5.1f}  "
          f"{blind_ari(didx,files,y,False):8.3f} {blind_ari(didx,files,y,True):9.3f}")
    print()

# figure: for A-B and B-C, show class-avg difference + diffmask contour (side-on)
fig,ax=plt.subplots(1,2,figsize=(9,5))
for a,(c1,c2) in zip(ax,[("A","B"),("B","C")]):
    d=np.abs(avg[c1]-avg[c2]); xc=d.shape[2]//2
    a.imshow(d[:,:,xc].T,cmap="magma",origin="lower")
    a.contour(masks_for_fig[(c1,c2)][:,:,xc].T,levels=[0.5],colors="cyan",linewidths=1.2)
    a.set_title(f"|avg {c1} - avg {c2}| + diff mask (cyan)",fontsize=10)
    a.set_xlabel("Z"); a.set_ylabel("Y")
fig.suptitle("Difference mask circles only where the two class averages differ",fontsize=11)
fig.tight_layout(rect=[0,0,1,0.95])
fig.savefig(os.path.join(QC,"diffmask_overlay.png"),dpi=120)
print("saved",os.path.join(QC,"diffmask_overlay.png"))
