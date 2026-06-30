#!/usr/bin/env python3
"""Setup Dynamo dpkpca inputs for T3SS injectisome dataset.

Creates:
  dynamo_outputs/t3ss_pca/data/particle_00001.mrc .. particle_00415.mrc
    (symlinks to merged_BC_t3ss/*.mrc, 1-based)
  dynamo_outputs/t3ss_pca/t3ss_pca.tbl
    (35-col Dynamo table, identity poses)
"""
import os, csv

PARTICLES = os.path.expanduser(
    "~/Research/synthetic_sta/injectisome/subtomos/merged_BC_t3ss")
OUT_DIR   = os.path.expanduser(
    "~/Research/STA/packages/dynamo/dynamo_outputs/t3ss_pca")
DATA_DIR  = os.path.join(OUT_DIR, "data")
TBL_FILE  = os.path.join(OUT_DIR, "t3ss_pca.tbl")

os.makedirs(DATA_DIR, exist_ok=True)

with open(os.path.join(PARTICLES, "labels.csv")) as f:
    rows = list(csv.DictReader(f))
N = len(rows)
print(f"Found {N} particles")

for i, row in enumerate(rows):
    tag  = i + 1
    link = os.path.join(DATA_DIR, f"particle_{tag:05d}.mrc")
    target = os.path.join(PARTICLES, row["file"])
    if os.path.lexists(link):
        os.remove(link)
    os.symlink(target, link)
print(f"Created {N} symlinks in {DATA_DIR}")

with open(TBL_FILE, "w") as f:
    for i in range(N):
        tag = i + 1
        row = [0.0] * 35
        row[0] = tag
        row[1] = 1    # active
        row[5] = 1    # tomogram 1
        f.write(" ".join(str(int(v) if v == int(v) else v) for v in row) + "\n")
print(f"Wrote {TBL_FILE} ({N} rows)")
print("Next: run dynamo_t3ss_pca.m under MATLAB")
