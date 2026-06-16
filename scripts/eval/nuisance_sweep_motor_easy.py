#!/usr/bin/env python3
"""
Isolate the real bottleneck: hold SNR at the realistic 0.42 + a missing wedge,
and sweep the PER-PARTICLE ORIENTATION SPREAD (random azimuth about the motor
axis). Each particle's wedge then sits at a different orientation -> inter-particle
nuisance variance that does NOT average away. Shows blind PCA+kmeans ARI collapse
as orientation spread grows, while SNR is fixed. Contrast: SNR alone (prev sweep)
gave ARI=1.0 at all levels.

Geometry: motor axis = box Y; electron beam = box Z; single-axis tilt about X
(+-60 deg) -> missing wedge around kZ in the kZ-kY plane. A per-particle azimuth
theta about Y rotates the wedge relative to the particle.

Run: conda run -n relion-5.0 python3 scripts/eval/nuisance_sweep_motor_easy.py
"""
import os, numpy as np, mrcfile
from scipy.ndimage import gaussian_filter, rotate
from sklearn.decomposition import PCA
from sklearn.cluster import KMeans
from sklearn.metrics import adjusted_rand_score as ARI
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt

QC = "/home/jblaser2/Research/STA/outputs/FM_easy/input_qc"
MAPS = "/home/jblaser2/Research/synthetic_sta/motor_easy/maps"
clean = {c: np.asarray(mrcfile.open(f"{MAPS}/class_{n}.mrc", permissive=True).data, np.float32)
         for c, n in [("A","A_full"),("B","B_noCring"),("C","C_noRodHook")]}
N = 96
z,y,x = np.mgrid[0:N,0:N,0:N].astype(np.float32)
MASK = np.sqrt((x-48)**2+(y-38)**2+(z-48)**2) <= 22
SNR = 0.42

# missing wedge: beam=Z, tilt about X, +-60 deg -> missing within 30 deg of kZ (in kZ-kY)
kz,ky,kx = np.meshgrid(np.fft.fftfreq(N),np.fft.fftfreq(N),np.fft.fftfreq(N),indexing="ij")
theta_from_Z = np.degrees(np.arctan2(np.abs(ky), np.abs(kz)+1e-9))
WEDGE = (theta_from_Z >= (90-60)).astype(np.float32)
def wedge(v): return np.real(np.fft.ifftn(np.fft.fftn(v)*WEDGE)).astype(np.float32)

sig_var = {p: np.var(np.concatenate([clean[p[0]][MASK], clean[p[1]][MASK]])) for p in [("A","C"),("B","C"),("A","B")]}

def run(c1, c2, jitter_deg, nper=80, seeds=2):
    nstd = np.sqrt(sig_var[(c1,c2)]/SNR)
    aris=[]
    for sd in range(seeds):
        rng=np.random.default_rng(sd); X=[]; yl=[]
        for cc,lab in [(c1,0),(c2,1)]:
            base=clean[cc]
            for _ in range(nper):
                th=rng.uniform(-jitter_deg,jitter_deg)
                v=rotate(base,th,axes=(0,2),reshape=False,order=1) if jitter_deg>0 else base  # azimuth about Y
                v=wedge(v)                                   # particle-frame wedge (fixed lab dir)
                v=v+rng.normal(0,nstd,v.shape).astype(np.float32)
                v=gaussian_filter(v,1.5); xx=v[MASK]; X.append((xx-xx.mean())/(xx.std()+1e-6)); yl.append(lab)
        X=np.asarray(X); X-=X.mean(0); yl=np.array(yl)
        Z=PCA(20,svd_solver="randomized",random_state=0).fit_transform(X)
        aris.append(ARI(yl,KMeans(2,n_init=10,random_state=0).fit(Z).labels_))
    return float(np.mean(aris))

JIT=[0,10,30,90,180]
PAIRS=[("A","C"),("B","C"),("A","B")]
print(f"SNR fixed at {SNR} + missing wedge | mask r=22 | sweep azimuth jitter about motor axis\n")
print("jitter(deg)  "+"  ".join(f"{a}-{b}" for a,b in PAIRS))
res={}
for j in JIT:
    row=[run(a,b,j) for a,b in PAIRS]; res[j]=row
    print(f"{j:8d}     "+"  ".join(f"{v:5.2f}" for v in row))
fig,ax=plt.subplots(figsize=(7,5))
for k,(a,b) in enumerate(PAIRS):
    ax.plot(JIT,[res[j][k] for j in JIT],"o-",label=f"{a}-{b}")
ax.set_xlabel("per-particle azimuth jitter about motor axis (deg)"); ax.set_ylabel("blind PCA+kmeans ARI")
ax.set_title(f"Orientation/wedge nuisance kills blind separation (SNR fixed at {SNR})")
ax.axhline(0.5,color="gray",ls=":"); ax.legend(); ax.grid(alpha=0.3)
fig.tight_layout(); fig.savefig(f"{QC}/nuisance_sweep.png",dpi=120); print("saved",f"{QC}/nuisance_sweep.png")
