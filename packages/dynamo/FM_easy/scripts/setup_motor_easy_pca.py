#!/usr/bin/env python3
"""
Setup input data folder and Dynamo table for motor_easy dpkpca run.

Creates:
  dynamo_outputs/motor_easy_pca/data/particle_00001.mrc .. particle_00694.mrc
    (symlinks to merged_all_aln/*.mrc; particle indices are 1-based)
  dynamo_outputs/motor_easy_pca/motor_easy_pca.tbl
    (Dynamo table: 35 cols, col1=tag, rest=0, identity poses)
"""
import os, csv

ALN_DIR  = os.path.expanduser(
    "~/Research/synthetic_sta/motor_easy/production/subtomos/merged_all_aln")
OUT_DIR  = os.path.expanduser(
    "~/Research/STA/packages/dynamo/dynamo_outputs/motor_easy_pca")
DATA_DIR = os.path.join(OUT_DIR, "data")
TBL_FILE = os.path.join(OUT_DIR, "motor_easy_pca.tbl")

os.makedirs(DATA_DIR, exist_ok=True)

# Read GT-ordered file list from labels.csv
with open(os.path.join(ALN_DIR, "labels.csv")) as f:
    files = [row["file"] for row in csv.DictReader(f)]
N = len(files)
print(f"Found {N} particles")

# Create symlinks: particle_XXXXX.mrc -> merged_all_aln/subtomo_XXXX.mrc
# Dynamo uses 5-digit 1-based tag for filenames
for i, fname in enumerate(files):
    tag = i + 1
    link = os.path.join(DATA_DIR, f"particle_{tag:05d}.mrc")
    target = os.path.join(ALN_DIR, fname)
    if os.path.lexists(link):
        os.remove(link)
    os.symlink(target, link)

print(f"Created {N} symlinks in {DATA_DIR}")

# Write Dynamo table: 35 columns, col1=tag, rest=0
# Col 1: tag; cols 7-9: Euler angles (ZXZ: tdrot,tilt,narot); cols 24-26: shifts (x,y,z)
# All zeros = identity pose = no alignment correction needed
with open(TBL_FILE, "w") as f:
    for i in range(N):
        tag = i + 1
        row = [0.0] * 35
        row[0] = tag          # col 1: particle tag (1-based)
        row[1] = 1            # col 2: flag (1 = active)
        row[5] = 1            # col 6: tomogram number
        f.write(" ".join(str(int(v) if v == int(v) else v) for v in row) + "\n")

print(f"Wrote {TBL_FILE} ({N} rows, 35 cols, identity poses)")
print(f"\nNext: run dynamo_motor_easy_pca.m")
