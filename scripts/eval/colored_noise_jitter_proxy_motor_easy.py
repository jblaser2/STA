#!/usr/bin/env python3
"""
Extends colored_noise_snr_proxy: adds PER-PARTICLE pose jitter (the one thing the
clean proxy lacked). The clean proxy (wedge + measured colored noise, identical signal
per class) separates A-vs-C at ARI~1 even at the real SNR 0.21 -- so SNR/wedge/colored
noise are NOT the wall. Hypothesis: per-particle registration variance is.

Two sweeps:
  (1) fix SNR=0.42, sweep pose jitter -> find the jitter that reproduces real ARI~0
  (2) fix jitter at that collapse level, sweep SNR -> does more signal rescue it?
If (2) stays ~0, SNR is a dead lever and the wall is registration variance.
"""
import os, numpy as np, mrcfile, csv
from numpy.fft import fftn, ifftn, fftshift
from scipy.ndimage import affine_transform
from scipy.spatial.transform import Rotation
from math import comb

MAPS = os.path.expanduser("~/Research/synthetic_sta/motor_easy/maps")
ALN  = os.path.expanduser("~/Research/synthetic_sta/motor_easy/production/subtomos/merged_all_aln")
MASK = os.path.expanduser("~/Research/STA/packages/dynamo/dynamo_outputs/easy_pair_AC/diff_sphere_r23_y55.mrc")
LAB  = os.path.expanduser("~/Research/STA/packages/dynamo/dynamo_outputs/easy_pair_AC/pair_labels.csv")
def rd(p): return mrcfile.open(p,permissive=True).data.astype(np.float32)

A = rd(os.path.join(MAPS,"class_A_full.mrc")); C = rd(os.path.join(MAPS,"class_C_noRodHook.mrc"))
mask = rd(MASK); N=A.shape[0]; ctr=(N-1)/2.0

# wedge (+/-60 about X, along Z)
kz,ky,kx=np.mgrid[0:N,0:N,0:N].astype(np.float32); kz-=N//2; ky-=N//2; kx-=N//2
measured=(np.abs(kz)<=np.abs(ky)*np.tan(np.deg2rad(60))+1e-6); measured[(ky==0)&(kz==0)]=True
wedge=fftshift(measured.astype(np.float32))
def apply_wedge(v): return np.real(ifftn(fftn(v)*wedge)).astype(np.float32)

# noise PSD from real class-A
labels={r['orig_file']:r['gt_label'] for r in csv.DictReader(open(LAB))}
Afiles=[os.path.join(ALN,f) for f,l in labels.items() if l=='A']
accp=np.zeros((N,N,N)); accF=np.zeros((N,N,N),complex); nA=0
for f in Afiles:
    v=rd(f); v=(v-v.mean())/(v.std()+1e-9); F=fftn(v); accp+=np.abs(F)**2; accF+=F; nA+=1
noisePSD=np.clip(accp/nA-np.abs(accF/nA)**2,0,None)
print(f"noise PSD from {nA} real A subtomos")

# snr metric
zz,yy,xx=np.mgrid[0:N,0:N,0:N]; r=np.sqrt((xx-ctr)**2+(yy-ctr)**2+(zz-ctr)**2)
particle=r<0.30*N; bg=r>0.425*N
def snr_of(st): return st.mean(0)[particle].std()/(st[:,bg].std(axis=1).mean()+1e-9)
def norm_sig(v): m=v[particle]; return (v-v.mean())/(m.std()+1e-9)

# blind classifier
mvox=mask>0.05
def kmeans2(X,it=100):
    rs=np.random.default_rng(42); cen=X[rs.choice(len(X),2,replace=False)].copy()
    for _ in range(it):
        lab=((X[:,None,:]-cen[None])**2).sum(-1).argmin(1)
        new=np.array([X[lab==k].mean(0) if (lab==k).any() else cen[k] for k in range(2)])
        if np.allclose(new,cen): break
        cen=new
    return lab
def ari(a,b):
    la=sorted(set(a)); lb=sorted(set(b)); M=np.zeros((len(la),len(lb)),int)
    ia={v:i for i,v in enumerate(la)}; ib={v:i for i,v in enumerate(lb)}
    for x,y in zip(a,b): M[ia[x],ib[y]]+=1
    sc=sum(comb(int(v),2) for v in M.sum(0)); sr=sum(comb(int(v),2) for v in M.sum(1))
    si=sum(comb(int(v),2) for v in M.flat); n=comb(len(a),2); e=sr*sc/n; mx=(sr+sc)/2
    return (si-e)/(mx-e) if mx!=e else 0.0
def classify(st,gt):
    X=st.reshape(len(st),-1)[:,mvox.ravel()]; X=X-X.mean(0)
    U,S,Vt=np.linalg.svd(X,full_matrices=False); Z=U[:,:10]*S[:10]
    return ari(gt,kmeans2(Z))

def jitter_vol(v, rot_deg, sh_px, rs):
    if rot_deg<=0 and sh_px<=0: return v
    ax=rs.standard_normal(3); ax/=np.linalg.norm(ax)+1e-9
    Rm=Rotation.from_rotvec(np.deg2rad(rot_deg)*ax).as_matrix()
    off=ctr-Rm@np.array([ctr]*3)+ rs.standard_normal(3)*sh_px
    return affine_transform(v,Rm,offset=off,order=1,mode='nearest').astype(np.float32)

NA=NC=90; gt=[0]*NA+[1]*NC
An,Cn=norm_sig(apply_wedge(A)),norm_sig(apply_wedge(C))
A0,C0=norm_sig(A),norm_sig(C)  # pre-wedge clean for jitter-then-wedge

def build(c, rot_deg, sh_px, seed):
    rs=np.random.default_rng(seed); st=[]
    for src in (A0,)*NA+(C0,)*NC:
        sig=apply_wedge(jitter_vol(src,rot_deg,sh_px,rs))
        g=(rs.standard_normal((N,N,N))+1j*rs.standard_normal((N,N,N)))/np.sqrt(2)
        st.append(c*norm_sig(sig)+np.real(ifftn(np.sqrt(noisePSD)*g)).astype(np.float32))
    return np.array(st,np.float32)

# calibrate contrast->SNR using a mid build
snr1=snr_of(build(1.0,0,0,1)); print(f"SNR at contrast=1.0: {snr1:.3f}\n")
def c_for(target): return target/snr1

print("=== SWEEP 1: fix SNR=0.42, vary pose jitter ===")
print(f"{'rot_deg':>7} {'sh_px':>6} {'measSNR':>8} {'ARI':>7}")
for rotd in [0,5,10,15,20,30,40]:
    shp=rotd/10.0
    st=build(c_for(0.42),rotd,shp,200+rotd); print(f"{rotd:7d} {shp:6.1f} {snr_of(st):8.3f} {classify(st,gt):7.3f}")

print("\n=== SWEEP 2: vary SNR at fixed jitter, ARI averaged over 5 seeds ===")
def mean_ari(c,rotd,shp,nseed=5):
    vals=[classify(build(c,rotd,shp,1000*int(rotd)+37*s+int(c*100)),gt) for s in range(nseed)]
    return np.mean(vals), np.std(vals)
for ROTJ,SHJ in [(20,2.0),(30,3.0)]:
    print(f"\n-- jitter {ROTJ}deg/{SHJ}px (reproduces real failure) --")
    print(f"{'targetSNR':>9} {'ARI_mean':>9} {'ARI_std':>8}")
    for tgt in [0.21,0.42,1.0,2.0,4.0,8.0]:
        m,s=mean_ari(c_for(tgt),ROTJ,SHJ); print(f"{tgt:9.2f} {m:9.3f} {s:8.3f}")
print("\nReal data: SNR~0.21, ARI~0 (Dynamo/RELION).")
