#!/usr/bin/env python3
"""
Setup input data folder and Dynamo table for motor_switch dpkpca run.

451 GT-aligned subtomograms (160³, 5 Å/px): 208 CCW + 208 CW + 35 junk.

Creates:
  dynamo_outputs/motor_switch_pca/data/particle_00001.mrc .. particle_00451.mrc
    (symlinks to all_particles_aligned/*.mrc; particle indices are 1-based)
  dynamo_outputs/motor_switch_pca/motor_switch_pca.tbl
    (Dynamo table: 35 cols, col1=tag, identity poses)
"""
import os, csv

ALN_DIR  = os.path.expanduser(
    "~/Research/synthetic_sta/motor_switch/production_5apix/subtomos/all_particles_aligned")
OUT_DIR  = os.path.expanduser(
    "~/Research/STA/packages/dynamo/dynamo_outputs/motor_switch_pca")
DATA_DIR = os.path.join(OUT_DIR, "data")
TBL_FILE = os.path.join(OUT_DIR, "motor_switch_pca.tbl")

os.makedirs(DATA_DIR, exist_ok=True)

with open(os.path.join(ALN_DIR, "labels.csv")) as f:
    files = [row["file"] for row in csv.DictReader(f)]
N = len(files)
print(f"Found {N} particles")

for i, fname in enumerate(files):
    tag = i + 1
    link = os.path.join(DATA_DIR, f"particle_{tag:05d}.mrc")
    target = os.path.join(ALN_DIR, fname)
    if os.path.lexists(link):
        os.remove(link)
    os.symlink(target, link)

print(f"Created {N} symlinks in {DATA_DIR}")

with open(TBL_FILE, "w") as f:
    for i in range(N):
        tag = i + 1
        row = [0.0] * 35
        row[0] = tag
        row[1] = 1
        row[5] = 1
        f.write(" ".join(str(int(v) if v == int(v) else v) for v in row) + "\n")

print(f"Wrote {TBL_FILE} ({N} rows, 35 cols, identity poses)")
print(f"\nNext: run dynamo_motor_switch_pca.m")
