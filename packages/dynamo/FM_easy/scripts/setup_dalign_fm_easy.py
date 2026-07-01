#!/usr/bin/env python3
"""Set up a Dynamo production-alignment (dalign) run on FM_easy hc particles.

Creates:
  dynamo_outputs/easy_AC_dalign/data/   — symlinks to merged_AC_full/ particles
  dynamo_outputs/easy_AC_dalign/pair.tbl — identity-pose Dynamo table
  dynamo_outputs/easy_AC_dalign/pair_labels.csv — tag, orig_file, gt_label
  dynamo_outputs/easy_AC_dalign/diff_sphere_r23_y55.mrc — classification mask copy
  dynamo_outputs/easy_AC_dalign/initial_ref.mrc — global average (initial template)

Run with any env that has mrcfile:
  conda run -n eman2 python3 packages/dynamo/FM_easy/scripts/setup_dalign_fm_easy.py
"""
import os, csv, shutil
import numpy as np
import mrcfile

SRC    = os.path.expanduser("~/Research/synthetic_sta/motor_easy/hc_test_x6/subtomos/merged_AC_full")
OUT    = os.path.expanduser("~/Research/STA/packages/dynamo/dynamo_outputs/easy_AC_dalign")
MASK   = os.path.expanduser(
    "~/Research/STA/packages/dynamo/dynamo_outputs/easy_pair_AC_hc/diff_sphere_r23_y55.mrc")
APIX   = 13.329

DATA = os.path.join(OUT, "data")
os.makedirs(DATA, exist_ok=True)

# Remove stale symlinks
for f in os.listdir(DATA):
    if f.endswith(".mrc"):
        os.remove(os.path.join(DATA, f))

rows = list(csv.DictReader(open(os.path.join(SRC, "labels.csv"))))
n_A = sum(r["label"] == "A" for r in rows)
n_C = sum(r["label"] == "C" for r in rows)
print(f"FM_easy hc: {n_A} A + {n_C} C = {len(rows)} particles")

# Build pair.tbl + pair_labels.csv + symlinks
with open(os.path.join(OUT, "pair.tbl"), "w") as tf, \
     open(os.path.join(OUT, "pair_labels.csv"), "w", newline="") as lf:
    w = csv.writer(lf)
    w.writerow(["tag", "orig_file", "gt_label"])
    for i, r in enumerate(rows):
        tag = i + 1
        src_path = os.path.join(SRC, r["file"])
        dst_path = os.path.join(DATA, f"particle_{tag:05d}.mrc")
        os.symlink(src_path, dst_path)
        w.writerow([tag, r["file"], r["label"]])
        # Identity-pose Dynamo table row (35 columns)
        # Col 1=tag, 2=aligned(1), 3=averaged(0), 4-6=shifts(0), 7-9=euler(0),
        # 10=cc(0), 11=cc2(0), 12=cpu(0), 13=ftype(0=full sphere)
        row = [0.0] * 35
        row[0] = tag   # tag
        row[1] = 1     # aligned flag: mark for alignment
        row[12] = 0    # ftype=0: full sphere (no tilt-series missing wedge)
        tf.write(" ".join(str(int(v) if v == int(v) else v) for v in row) + "\n")

# Copy mask
shutil.copy(MASK, os.path.join(OUT, "diff_sphere_r23_y55.mrc"))
print(f"Mask copied: {os.path.join(OUT, 'diff_sphere_r23_y55.mrc')}")

# Compute initial reference (global average of all particles, masked)
print("Computing initial reference (global average)...")
avg = None
for i, r in enumerate(rows):
    with mrcfile.open(os.path.join(SRC, r["file"]), permissive=True) as m:
        v = m.data.astype(np.float32)
    if avg is None:
        avg = v.copy()
    else:
        avg += v
    if (i + 1) % 50 == 0:
        print(f"  averaged {i+1}/{len(rows)}")
avg /= len(rows)

# Per-volume normalize
avg -= avg.mean()
avg /= (avg.std() + 1e-6)

ref_path = os.path.join(OUT, "initial_ref.mrc")
with mrcfile.new(ref_path, overwrite=True) as m:
    m.set_data(avg)
    m.voxel_size = APIX
print(f"Initial reference: {ref_path}")
print(f"OUT = {OUT}")
