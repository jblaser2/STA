#!/usr/bin/env python3
"""Reference-based subtomogram alignment for FM_easy (the 'real alignment' step the GT-pose
particles never got). Iterative refinement of each particle's pose (sub-voxel translation via
FFT cross-correlation + rotational search on a downsampled copy) against the masked GLOBAL
average (single reference, no class info -> blind/fair). Cumulative pose is tracked and applied
ONCE to the original particle (cubic interp) to avoid compounding interpolation blur.

Writes  <ALN>/../merged_AC_aligned/{subtomo_XXXX.mrc, labels.csv}  (same names/labels as input).
Run with relion-5.0 env.  Usage: align_fm_easy.py [n_iter]
"""
import os, sys, csv, glob, numpy as np, mrcfile
from scipy.ndimage import affine_transform
from scipy.spatial.transform import Rotation
from math import comb

SRC="/home/jblaser2/Research/synthetic_sta/motor_easy/hc_test_x6/subtomos/merged_AC_full"
OUT="/home/jblaser2/Research/synthetic_sta/motor_easy/hc_test_x6/subtomos/merged_AC_aligned"
MASK="/home/jblaser2/Research/STA/packages/dynamo/dynamo_outputs/easy_pair_AC_hc/diff_sphere_r23_y55.mrc"
BOX=96; APIX=13.329; NITER=int(sys.argv[1]) if len(sys.argv)>1 else 4
os.makedirs(OUT, exist_ok=True)

mask=mrcfile.open(MASK,permissive=True).data.astype(np.float32); mb=mask>0.05
lab={r['file']:r['label'] for r in csv.DictReader(open(SRC+"/labels.csv"))}
files=sorted(glob.glob(SRC+"/subtomo_*.mrc")); names=[os.path.basename(f) for f in files]
orig=np.array([mrcfile.open(f,permissive=True).data.astype(np.float32) for f in files])
N=len(orig); print(f"{N} particles, {NITER} iters")

# bandpass for the alignment metric only (suppress contrast & high-freq noise)
c=BOX//2; ax=(np.arange(BOX)-c)/BOX
KZ,KY,KX=np.meshgrid(ax,ax,ax,indexing='ij'); KR=np.sqrt(KX**2+KY**2+KZ**2)
BP=((KR>=0.05)&(KR<=0.45)).astype(np.float32)
def bp(v): return np.real(np.fft.ifftn(np.fft.ifftshift(np.fft.fftshift(np.fft.fftn(v))*BP)))
def fshift(v,s):
    z=np.fft.fftfreq(BOX)
    ph=np.exp(-2j*np.pi*(s[0]*z[:,None,None]+s[1]*z[None,:,None]+s[2]*z[None,None,:]))
    return np.real(np.fft.ifftn(np.fft.fftn(v)*ph))
def ds(v,h=24):
    F=np.fft.fftshift(np.fft.fftn(v)); cc=BOX//2
    return np.real(np.fft.ifftn(np.fft.ifftshift(F[cc-h:cc+h,cc-h:cc+h,cc-h:cc+h])))
def apply_pose(v,R,t):
    cn=np.array(v.shape)/2.0-0.5
    vr=affine_transform(v,R,offset=cn-R@cn,order=3,mode='constant',cval=0.0)
    return fshift(vr,t)

Rc=[np.eye(3) for _ in range(N)]; tc=[np.zeros(3) for _ in range(N)]
m48=ds(mask)>0.2
rng=np.random.default_rng(0)
for it in range(NITER):
    amp=[15,10,6,4][min(it,3)]
    ROTS=[np.eye(3)]+[Rotation.from_rotvec(np.radians(rng.uniform(-amp,amp,3))).as_matrix() for _ in range(60)]
    cur=np.array([apply_pose(orig[i],Rc[i],tc[i]) for i in range(N)])
    ref=bp(cur.mean(0))*mask; ref48=ds(bp(cur.mean(0)))*m48
    Fr=np.conj(np.fft.fftn(ref))
    for i in range(N):
        # translation (full-res, bandpassed, masked) via FFT cross-correlation
        ccm=np.real(np.fft.ifftn(np.fft.fftn(bp(cur[i])*mask)*Fr))
        pk=np.unravel_index(np.argmax(ccm),ccm.shape); sh=np.array([(p if p<=BOX//2 else p-BOX) for p in pk])
        ci=fshift(cur[i],-sh)
        # rotation search on downsample
        v48=ds(bp(ci)); cn=np.array(v48.shape)/2-0.5; best=np.eye(3); bs=-1e18
        for R in ROTS:
            vr=v48 if np.allclose(R,np.eye(3)) else affine_transform(v48,R,offset=cn-R@cn,order=1,mode='constant')
            s=float((vr*ref48).sum())
            if s>bs: bs=s; best=R
        # accumulate: new cumulative pose = best ∘ shift ∘ current
        Rc[i]=best@Rc[i]; tc[i]=tc[i]-sh   # translation tracked in current frame (approx; sub-voxel residual small)
    print(f" iter {it+1} (rot±{amp}) done")

# write final aligned particles (apply cumulative pose once to ORIGINAL)
rows=[]
for i in range(N):
    va=apply_pose(orig[i],Rc[i],tc[i])
    with mrcfile.new(os.path.join(OUT,names[i]),overwrite=True) as m:
        m.set_data(va.astype(np.float32)); m.voxel_size=APIX
    rows.append({"file":names[i],"label":lab[names[i]]})
with open(os.path.join(OUT,"labels.csv"),"w",newline="") as f:
    w=csv.DictWriter(f,fieldnames=["file","label"]); w.writeheader(); [w.writerow(r) for r in rows]
print("wrote",OUT)

# sanity: blind masked-PCA ARI on the saved aligned set
al=np.array([mrcfile.open(os.path.join(OUT,n),permissive=True).data for n in names])
y=np.array([0 if lab[n]=='A' else 1 for n in names])
X=al.reshape(N,-1)[:,mb.ravel()]; X=X-X.mean(0)
U,S,Vt=np.linalg.svd(X,full_matrices=False); Z=U[:,:10]*S[:10]
def ari(a,b):
    la=sorted(set(a)); lb=sorted(set(b)); M=np.zeros((len(la),len(lb)),int)
    ia={v:i for i,v in enumerate(la)}; ib={v:i for i,v in enumerate(lb)}
    for x,z in zip(a,b): M[ia[x],ib[z]]+=1
    sc=sum(comb(int(v),2) for v in M.sum(0)); sr=sum(comb(int(v),2) for v in M.sum(1))
    si=sum(comb(int(v),2) for v in M.flat); nn=comb(len(a),2); e=sr*sc/nn; mx=(sr+sc)/2
    return (si-e)/(mx-e) if mx!=e else 0.0
aris=[]
for s in range(20):
    rs=np.random.default_rng(s); cen=Z[rs.choice(N,2,replace=False)].copy()
    for _ in range(200):
        d=((Z[:,None,:]-cen[None])**2).sum(-1).argmin(1)
        new=np.array([Z[d==k].mean(0) if (d==k).any() else cen[k] for k in range(2)])
        if np.allclose(new,cen): break
        cen=new
    aris.append(ari(y,d))
print(f"blind masked-PCA ARI on aligned set: {np.mean(aris):.3f}+/-{np.std(aris):.3f}  (GT-pose baseline was 0.14)")
