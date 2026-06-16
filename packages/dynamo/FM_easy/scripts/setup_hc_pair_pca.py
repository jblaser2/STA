#!/usr/bin/env python3
"""Set up a Dynamo dpkpca run on the HIGH-CONTRAST (x6) A/C aligned subtomos.
Symlinks the 354 hc particles, builds pair.tbl + pair_labels.csv, copies the diff mask."""
import os, csv, shutil
ALN = os.path.expanduser("~/Research/synthetic_sta/motor_easy/hc_test_x6/subtomos/merged_AC_full")
OUT = os.path.expanduser("~/Research/STA/packages/dynamo/dynamo_outputs/easy_pair_AC_hc")
SRCMASK = os.path.expanduser("~/Research/STA/packages/dynamo/dynamo_outputs/easy_pair_AC/diff_sphere_r23_y55.mrc")
DATA = os.path.join(OUT, "data"); os.makedirs(DATA, exist_ok=True)
for f in os.listdir(DATA):
    if f.endswith(".mrc"): os.remove(os.path.join(DATA, f))

rows = list(csv.DictReader(open(os.path.join(ALN, "labels.csv"))))
print(f"hc set: {sum(r['label']=='A' for r in rows)} A + {sum(r['label']=='C' for r in rows)} C = {len(rows)}")
with open(os.path.join(OUT,"pair_labels.csv"),"w",newline="") as lf, open(os.path.join(OUT,"pair.tbl"),"w") as tf:
    w=csv.writer(lf); w.writerow(["tag","orig_file","gt_label"])
    for i,r in enumerate(rows):
        tag=i+1
        os.symlink(os.path.join(ALN,r["file"]), os.path.join(DATA,f"particle_{tag:05d}.mrc"))
        w.writerow([tag,r["file"],r["label"]])
        row=[0.0]*35; row[0]=tag; row[1]=1; row[5]=1
        tf.write(" ".join(str(int(v) if v==int(v) else v) for v in row)+"\n")
shutil.copy(SRCMASK, os.path.join(OUT,"diff_sphere_r23_y55.mrc"))
print("OUT=",OUT)
