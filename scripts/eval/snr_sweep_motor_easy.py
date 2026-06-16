#!/usr/bin/env python3
"""
SNR threshold sweep for blind classification of motor_easy class pairs.

For each SNR level, synthesize a population of particles = clean class map + white
Gaussian noise (optionally after a ±60 deg missing wedge along the motor axis),
then run the SAME blind masked-PCA + k-means used on the real data. Finds the SNR
at which ARI lifts off zero. Real-data SNR (~0.42, T4P-matched) is marked.

NOTE: white-noise + perfect-alignment + single-axis wedge are idealizations, so the
thresholds here are OPTIMISTIC vs the real WBP subtomos (colored noise, residual
jitter). They bracket the design target.

Run: conda run -n relion-5.0 python3 scripts/eval/snr_sweep_motor_easy.py
"""
import os, numpy as np, mrcfile
from scipy.ndimage import gaussian_filter
from sklearn.decomposition import PCA
from sklearn.cluster import KMeans
from sklearn.metrics import adjusted_rand_score as ARI
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt

QC = "/home/jblaser2/Research/STA/outputs/FM_easy/input_qc"
MAPS = "/home/jblaser2/Research/synthetic_sta/motor_easy/maps"
clean = {c: np.asarray(mrcfile.open(f"{MAPS}/class_{n}.mrc", permissive=True).data, np.float32)
         for c, n in [("A","A_full"),("B","B_noCring"),("C","C_noRodHook")]}
N = 96
# generic spherical mask r=22 (best radius), center (48,38,48)
z,y,x = np.mgrid[0:N,0:N,0:N].astype(np.float32)
r = np.sqrt((x-48)**2+(y-38)**2+(z-48)**2); MASK = r <= 22

# missing wedge around the MOTOR axis (box Y): beam->Y after extraction-rotation.
# In Fourier (kz,ky,kx) zero where angle from kY axis (in kY-kX plane) < (90-alpha).
def wedge_filter(alpha_deg=60):
    kz,ky,kx = np.meshgrid(np.fft.fftfreq(N),np.fft.fftfreq(N),np.fft.fftfreq(N),indexing="ij")
    # motor axis = Y; beam direction maps to Y; tilt axis = Z. Missing wedge spans
    # +-(90-alpha) around kY in the kY-kX plane (perp to tilt axis kZ).
    ang = np.degrees(np.arctan2(np.abs(kx), np.abs(ky)+1e-9))   # angle from kY toward kX
    keep = ang >= (90-alpha_deg)
    return keep.astype(np.float32)
WEDGE = wedge_filter(60)

def apply_wedge(v):
    return np.real(np.fft.ifftn(np.fft.fftn(v)*WEDGE)).astype(np.float32)

def sweep_pair(c1, c2, snr, use_wedge, npc=20, nper=100, seeds=3):
    s1 = apply_wedge(clean[c1]) if use_wedge else clean[c1]
    s2 = apply_wedge(clean[c2]) if use_wedge else clean[c2]
    sig_var = np.var(np.concatenate([s1[MASK], s2[MASK]]))
    nstd = np.sqrt(sig_var/snr)
    aris = []
    for sd in range(seeds):
        rng = np.random.default_rng(sd)
        X=[]; ylab=[]
        for s, lab in [(s1,0),(s2,1)]:
            for _ in range(nper):
                v = gaussian_filter(s + rng.normal(0, nstd, s.shape).astype(np.float32), 1.5)
                xx = v[MASK]; X.append((xx-xx.mean())/(xx.std()+1e-6)); ylab.append(lab)
        X=np.asarray(X); X-=X.mean(0); ylab=np.array(ylab)
        Z=PCA(npc,svd_solver="randomized",random_state=0).fit_transform(X)
        km=KMeans(2,n_init=10,random_state=0).fit(Z).labels_
        aris.append(ARI(ylab,km))
    return float(np.mean(aris))

SNRS = [0.05,0.1,0.2,0.42,0.8,1.6,3.2,6.4,12.8]
PAIRS = [("A","C"),("B","C"),("A","B")]
print(f"mask r=22 ({100*MASK.mean():.1f}% box) | nper=100/class | 3 seeds | real SNR~0.42\n")
results = {}
for wedge in (False, True):
    tag = "NOISE + MISSING WEDGE (realistic)" if wedge else "NOISE ONLY (pure SNR floor)"
    print(f"=== {tag} ===")
    print("SNR   " + "  ".join(f"{a}-{b}" for a,b in PAIRS))
    for snr in SNRS:
        row=[sweep_pair(a,b,snr,wedge) for a,b in PAIRS]
        results[(wedge,snr)]=row
        mark = "  <- real data SNR" if snr==0.42 else ""
        print(f"{snr:5.2f} " + "  ".join(f"{v:5.2f}" for v in row) + mark)
    print()

# plot
fig,ax=plt.subplots(1,2,figsize=(12,5),sharey=True)
for a,wedge in zip(ax,(False,True)):
    for j,(c1,c2) in enumerate(PAIRS):
        a.plot(SNRS,[results[(wedge,s)][j] for s in SNRS],"o-",label=f"{c1}-{c2}")
    a.axvline(0.42,color="k",ls="--",lw=1); a.text(0.42,0.92,"real SNR",rotation=90,va="top",fontsize=8)
    a.axhline(0.5,color="gray",ls=":",lw=1)
    a.set_xscale("log"); a.set_xlabel("SNR (signal var / noise var)"); a.set_title(
        "noise + missing wedge" if wedge else "noise only"); a.legend(); a.grid(alpha=0.3)
ax[0].set_ylabel("blind PCA+kmeans ARI")
fig.suptitle("SNR threshold for blind separation of motor_easy class pairs",fontsize=12)
fig.tight_layout(rect=[0,0,1,0.95])
fig.savefig(f"{QC}/snr_sweep.png",dpi=120); print("saved",f"{QC}/snr_sweep.png")
