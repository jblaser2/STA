#!/usr/bin/env python3
"""Same difference sphere but translated +12 voxels in Y ('down' in the side view)."""
import csv, os, numpy as np, mrcfile
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt

OUT = os.path.dirname(os.path.abspath(__file__))
ALN = os.path.expanduser("~/Research/synthetic_sta/motor_easy/production/subtomos/merged_all_aln")
rows = list(csv.DictReader(open(os.path.join(OUT,'pair_labels.csv'))))

def classavg(cls):
    fs=[r['orig_file'] for r in rows if r['gt_label']==cls]; acc=None
    for f in fs:
        with mrcfile.open(os.path.join(ALN,f),permissive=True) as m: v=m.data.astype(np.float32)
        acc=v if acc is None else acc+v
    return acc/len(fs)

A,C = classavg('A'), classavg('C'); diff=A-C; N=A.shape[0]

# original diff centroid, then shift DOWN (+Y) by 12
cx_, cy0, cz_ = 48.2, 40.3, 47.8
DY = 15.0
cy_ = cy0 + DY
R = 23.0; edge=4.0
print(f"center shifted (x,y,z)=({cx_:.0f},{cy0:.0f}->{cy_:.0f},{cz_:.0f})  R={R:.0f}px  DY=+{DY:.0f}")

z,y,x = np.mgrid[0:N,0:N,0:N].astype(np.float32)
r=np.sqrt((x-cx_)**2+(y-cy_)**2+(z-cz_)**2)
m=np.ones_like(r); ine=(r>R)&(r<=R+edge)
m[ine]=0.5*(1+np.cos(np.pi*(r[ine]-R)/edge)); m[r>R+edge]=0.0
maskp=os.path.join(OUT,f"diff_sphere_r{int(R)}_y{int(cy_)}.mrc")
with mrcfile.new(maskp,overwrite=True) as o: o.set_data(m.astype(np.float32)); o.voxel_size=13.329
frac=100*float((m>0.05).mean()); print(f"mask -> {maskp}  ({frac:.1f}% box)")

cx=int(round(cx_)); cz=int(round(cz_))
fig,axs=plt.subplots(2,4,figsize=(15,7.6))
def show(ax,img,t,cmap='gray'): ax.imshow(img,cmap=cmap); ax.set_title(t,fontsize=10); ax.axis('off')
show(axs[0,0],A[cz],f"A avg (z={cz})"); show(axs[0,1],C[cz],f"C avg (z={cz})")
show(axs[0,2],diff[cz],f"A-C diff (z={cz})",'seismic'); show(axs[0,3],A[cz],f"mask over A (z={cz})")
axs[0,3].contour(m[cz],levels=[0.5],colors='red',linewidths=1.6)
axs[0,3].contourf(m[cz],levels=[0.05,1.0],colors=['red'],alpha=0.25)
show(axs[1,0],A[:,:,cx].T,f"A side (x={cx})"); show(axs[1,1],C[:,:,cx].T,f"C side (x={cx})")
show(axs[1,2],diff[:,:,cx].T,f"A-C diff side (x={cx})",'seismic'); show(axs[1,3],A[:,:,cx].T,f"mask over A side (x={cx})")
axs[1,3].contour(m[:,:,cx].T,levels=[0.5],colors='red',linewidths=1.6)
axs[1,3].contourf(m[:,:,cx].T,levels=[0.05,1.0],colors=['red'],alpha=0.25)
plt.suptitle(f"Diff sphere shifted +12 in Y  center(x,y,z)=({cx_:.0f},{cy_:.0f},{cz_:.0f})  R={R:.0f}px  [{frac:.1f}% box]",fontsize=12)
plt.tight_layout(); pv=os.path.join(OUT,'diff_mask_shift_preview.png'); plt.savefig(pv,dpi=140); plt.close()
print("saved",pv)
