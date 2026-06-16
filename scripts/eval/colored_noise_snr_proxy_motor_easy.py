#!/usr/bin/env python3
"""
Faithful colored-noise SNR proxy for the FM_easy A-vs-C task.

Earlier SNR sweep used WHITE noise + clean maps (no wedge) -> separated at any SNR,
which is unrealistic. This proxy keeps the two things that actually defeat the real
data and that the white sweep faked away:
  (1) the REAL missing wedge (single-axis tilt about X, +/-60 deg), applied along Z
  (2) COLORED noise whose 3D power spectrum is MEASURED from the real subtomos

Procedure:
  - clean A,C maps -> apply the same Z-wedge to both (matches the common-mode wedge
    seen in the real aligned subtomos)
  - estimate noise PSD from real class-A subtomos:  noisePSD = mean|F_i|^2 - |mean F_i|^2
  - synthesize per-particle colored noise from that PSD
  - sweep particle contrast c to hit a target SNR (snr_proxy metric), build N_A+N_C,
    classify blind (masked PCA + kmeans, diff mask) -> ARI vs GT
  - SANITY: at the measured real SNR (~0.21) the proxy should give ARI ~ 0, matching
    the real Dynamo/RELION runs. If it does, rising ARI at higher SNR is credible.
"""
import os, glob, numpy as np, mrcfile
from numpy.fft import fftn, ifftn, fftshift
from math import comb

MAPS = os.path.expanduser("~/Research/synthetic_sta/motor_easy/maps")
ALN  = os.path.expanduser("~/Research/synthetic_sta/motor_easy/production/subtomos/merged_all_aln")
MASK = os.path.expanduser("~/Research/STA/packages/dynamo/dynamo_outputs/easy_pair_AC/diff_sphere_r23_y55.mrc")
import csv
LAB  = os.path.expanduser("~/Research/STA/packages/dynamo/dynamo_outputs/easy_pair_AC/pair_labels.csv")
rng = np.random.default_rng(0)

def rd(p): return mrcfile.open(p, permissive=True).data.astype(np.float32)

A = rd(os.path.join(MAPS,"class_A_full.mrc"))
C = rd(os.path.join(MAPS,"class_C_noRodHook.mrc"))
mask = rd(MASK); N = A.shape[0]

# ---- 1. build the +/-60 single-axis (about X) missing wedge along Z ----
kz, ky, kx = np.mgrid[0:N,0:N,0:N].astype(np.float32)
kz-=N//2; ky-=N//2; kx-=N//2
ALPHA = np.deg2rad(60.0)
# measured if angle of (ky,kz) from kY axis <= ALPHA  <=> |kz| <= |ky|*tan(ALPHA)
with np.errstate(divide='ignore', invalid='ignore'):
    measured = (np.abs(kz) <= np.abs(ky)*np.tan(ALPHA) + 1e-6)
measured[ (ky==0)&(kz==0) ] = True
wedge = fftshift(measured.astype(np.float32))   # 1 where data exists, 0 in missing wedge

def apply_wedge(v):
    return np.real(ifftn(fftn(v)*wedge)).astype(np.float32)

Aw, Cw = apply_wedge(A), apply_wedge(C)

# ---- 2. estimate noise PSD from real class-A subtomos ----
labels = {r['orig_file']: r['gt_label'] for r in csv.DictReader(open(LAB))}
Afiles = [os.path.join(ALN,f) for f,l in labels.items() if l=='A']
acc_p = np.zeros((N,N,N)); acc_F = np.zeros((N,N,N), complex); nA=0
for f in Afiles:
    v = rd(f); v = (v-v.mean())/(v.std()+1e-9)
    F = fftn(v); acc_p += np.abs(F)**2; acc_F += F; nA+=1
meanP = acc_p/nA; meanF = acc_F/nA
noisePSD = np.clip(meanP - np.abs(meanF)**2, 0, None)   # per-frequency noise variance
print(f"noise PSD estimated from {nA} real class-A subtomos")

def synth_noise():
    # complex spectrum with E|F|^2 = noisePSD, then real-space field
    g = (rng.standard_normal((N,N,N)) + 1j*rng.standard_normal((N,N,N)))/np.sqrt(2)
    n = np.real(ifftn(np.sqrt(noisePSD)*g)).astype(np.float32)
    return n

# ---- snr proxy metric (same as snr_proxy.py) ----
zz,yy,xx = np.mgrid[0:N,0:N,0:N]; c=(N-1)/2.0
r = np.sqrt((xx-c)**2+(yy-c)**2+(zz-c)**2)
particle = r < 0.30*N; bg = r > 0.425*N
def snr_of(stack):
    avg = stack.mean(0); sig = avg[particle].std()
    noise = stack[:,bg].std(axis=1).mean()
    return sig/(noise+1e-9)

# normalize clean signals to unit particle-std so contrast c maps cleanly to SNR
def norm_sig(v):
    m = v[particle]; return (v - v.mean())/(m.std()+1e-9)
Aw_n, Cw_n = norm_sig(Aw), norm_sig(Cw)

# ---- blind classifier: masked, mean-subtracted PCA(10) + kmeans(2) ----
mvox = mask > 0.05
def kmeans2(X, iters=100):
    rs = np.random.default_rng(42)
    ci = rs.choice(len(X),2,replace=False); cen = X[ci].copy()
    for _ in range(iters):
        d = ((X[:,None,:]-cen[None])**2).sum(-1); lab = d.argmin(1)
        new = np.array([X[lab==k].mean(0) if (lab==k).any() else cen[k] for k in range(2)])
        if np.allclose(new,cen): break
        cen=new
    return lab
def ari(a,b):
    la=sorted(set(a)); lb=sorted(set(b)); M=np.zeros((len(la),len(lb)),int)
    ia={v:i for i,v in enumerate(la)}; ib={v:i for i,v in enumerate(lb)}
    for x,y in zip(a,b): M[ia[x],ib[y]]+=1
    sc=sum(comb(int(v),2) for v in M.sum(0)); sr=sum(comb(int(v),2) for v in M.sum(1))
    si=sum(comb(int(v),2) for v in M.flat); n=comb(len(a),2); exp=sr*sc/n; mx=(sr+sc)/2
    return (si-exp)/(mx-exp) if mx!=exp else 0.0

def classify(stack, gt):
    X = stack.reshape(len(stack),-1)[:, mvox.ravel()]
    X = X - X.mean(0)
    U,S,Vt = np.linalg.svd(X, full_matrices=False)
    Z = U[:,:10]*S[:10]
    pred = kmeans2(Z)
    return ari(gt, pred)

NA, NC = 120, 120
gt = [0]*NA + [1]*NC
# contrast at c=1 -> measure SNR, then scale
def build(c, seed=0):
    global rng; rng=np.random.default_rng(seed)
    st=[]
    for _ in range(NA): st.append(c*Aw_n + synth_noise())
    for _ in range(NC): st.append(c*Cw_n + synth_noise())
    return np.array(st, np.float32)

probe = build(1.0, seed=1)
snr1 = snr_of(probe)
print(f"SNR at contrast=1.0 : {snr1:.3f}\n")
print(f"{'targetSNR':>9} {'contrast':>9} {'measSNR':>8} {'ARI':>7}")
for target in [0.21, 0.4, 0.7, 1.0, 1.5, 2.5, 4.0, 8.0]:
    c = target/snr1
    st = build(c, seed=100+int(target*10))
    measured_snr = snr_of(st)
    a = classify(st, gt)
    print(f"{target:9.2f} {c:9.3f} {measured_snr:8.3f} {a:7.3f}")
print("\nReal data measured SNR ~0.21 (Dynamo/RELION ARI ~0).")
