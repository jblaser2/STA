#!/usr/bin/env python3
"""How far did refinement move particles from their GT (identity) poses?"""
import os, numpy as np
OUT = os.path.dirname(os.path.abspath(__file__))
star = os.path.join(OUT, "run_it015_data.star")
cols={}; rows=[]; inp=False
for line in open(star):
    s=line.strip()
    if s.startswith("data_particles"): inp=True; continue
    if inp and s.startswith("_rln"): cols[s.split()[0][1:]]=int(s.split("#")[1])-1; continue
    if inp and s and not s.startswith(("_","loop_","#","data")): rows.append(s.split())
def col(n): return cols.get(n)
rot=np.array([float(r[col("rlnAngleRot")]) for r in rows])
tilt=np.array([float(r[col("rlnAngleTilt")]) for r in rows])
psi=np.array([float(r[col("rlnAnglePsi")]) for r in rows])
ox=np.array([float(r[col("rlnOriginXAngst")]) for r in rows]) if col("rlnOriginXAngst") is not None else np.zeros(len(rows))
oy=np.array([float(r[col("rlnOriginYAngst")]) for r in rows]) if col("rlnOriginYAngst") is not None else np.zeros(len(rows))
oz=np.array([float(r[col("rlnOriginZAngst")]) for r in rows]) if col("rlnOriginZAngst") is not None else np.zeros(len(rows))
# angular magnitude from identity: treat (rot,tilt,psi); tilt is the main deviation from 0
ang = np.sqrt(rot**2 + tilt**2 + psi**2)   # rough magnitude in deg
shift_A = np.sqrt(ox**2+oy**2+oz**2)
apx=13.329
print(f"N={len(rows)}")
print(f"angle-from-identity (deg):  median={np.median(ang):.2f}  mean={ang.mean():.2f}  p90={np.percentile(ang,90):.2f}  max={ang.max():.2f}")
print(f"  |tilt| alone (deg):       median={np.median(np.abs(tilt)):.2f}  p90={np.percentile(np.abs(tilt),90):.2f}  max={np.abs(tilt).max():.2f}")
print(f"offset (Angstrom):          median={np.median(shift_A):.2f}  p90={np.percentile(shift_A,90):.2f}  max={shift_A.max():.2f}")
print(f"offset (voxels @ {apx}A):   median={np.median(shift_A)/apx:.2f}  p90={np.percentile(shift_A,90)/apx:.2f}  max={shift_A.max()/apx:.2f}")
print(f"frac moved >5deg: {100*np.mean(ang>5):.0f}%   frac moved >1vox: {100*np.mean(shift_A/apx>1):.0f}%")
