#!/usr/bin/env python3
"""
Set up a 2-class Dynamo dpkpca run on a PAIR of motor_easy GT classes, using ONLY
the raw GT-aligned subtomos + a generic spherical mask.

Usage: setup_easy_pair_pca.py <PAIR> <RADIUS_px>
  e.g. setup_easy_pair_pca.py AC 22

Creates packages/dynamo/dynamo_outputs/easy_pair_<PAIR>/:
  data/particle_00001.mrc ...   (symlinks to merged_all_aln, ONLY the 2 classes)
  pair.tbl                       (identity poses)
  pair_labels.csv                (tag, orig_file, gt_label)  -> for scoring
  sphere_r<R>.mrc                (soft spherical mask, center 48,38,48)
"""
import os, csv, sys
import numpy as np, mrcfile

PAIR = sys.argv[1].upper()
R    = float(sys.argv[2])
C1, C2 = PAIR[0], PAIR[1]

ALN = os.path.expanduser("~/Research/synthetic_sta/motor_easy/production/subtomos/merged_all_aln")
OUT = os.path.expanduser(f"~/Research/STA/packages/dynamo/dynamo_outputs/easy_pair_{PAIR}")
DATA = os.path.join(OUT, "data")
os.makedirs(DATA, exist_ok=True)

rows = [(r["file"], r["label"]) for r in csv.DictReader(open(os.path.join(ALN, "labels.csv")))]
sel = [(f, l) for f, l in rows if l in (C1, C2)]
print(f"pair {PAIR}: {sum(l==C1 for _,l in sel)} {C1} + {sum(l==C2 for _,l in sel)} {C2} = {len(sel)}")

# symlinks + table + label map
for old in os.listdir(DATA):
    if old.endswith(".mrc"):
        os.remove(os.path.join(DATA, old))
with open(os.path.join(OUT, "pair_labels.csv"), "w", newline="") as lf, \
     open(os.path.join(OUT, "pair.tbl"), "w") as tf:
    w = csv.writer(lf); w.writerow(["tag", "orig_file", "gt_label"])
    for i, (f, l) in enumerate(sel):
        tag = i + 1
        os.symlink(os.path.join(ALN, f), os.path.join(DATA, f"particle_{tag:05d}.mrc"))
        w.writerow([tag, f, l])
        row = [0.0]*35; row[0]=tag; row[1]=1; row[5]=1
        tf.write(" ".join(str(int(v) if v==int(v) else v) for v in row) + "\n")

# generic soft spherical mask, center (48,38,48) (same center as canonical FM_easy mask)
N, cx, cy, cz, edge = 96, 48, 38, 48, 4.0
z, y, x = np.mgrid[0:N, 0:N, 0:N].astype(np.float32)
r = np.sqrt((x-cx)**2 + (y-cy)**2 + (z-cz)**2)
m = np.ones_like(r); ine = (r > R) & (r <= R+edge)
m[ine] = 0.5*(1+np.cos(np.pi*(r[ine]-R)/edge)); m[r > R+edge] = 0.0
maskp = os.path.join(OUT, f"sphere_r{int(R)}.mrc")
with mrcfile.new(maskp, overwrite=True) as o:
    o.set_data(m.astype(np.float32)); o.voxel_size = 13.329
print(f"mask r={R}px -> {maskp}  ({100*float((m>0.05).mean()):.1f}% box)")
print(f"OUT={OUT}")
