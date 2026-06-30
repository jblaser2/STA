#!/usr/bin/env python3
"""Stack FM_hard MRC particles → particles.hdf + ptcls.lst + initial_ref.hdf
Run from: ~/Research/eman2_fm_hard/
"""
from EMAN2 import *
import os, csv

PARTICLES_DIR = os.path.expanduser(
    "~/Research/synthetic_sta/motor_hard/subtomos/merged_ABC_full")
LABELS_CSV = os.path.join(PARTICLES_DIR, "labels.csv")
APIX = 13.329

rows = list(csv.DictReader(open(LABELS_CSV)))
mrc_files = [os.path.join(PARTICLES_DIR, r["file"]) for r in rows]
print(f"Found {len(mrc_files)} particles (3 classes, no junk)")

out_hdf = "particles.hdf"
if os.path.exists(out_hdf):
    os.remove(out_hdf)

for i, f in enumerate(mrc_files):
    e = EMData(f)
    e["apix_x"] = e["apix_y"] = e["apix_z"] = APIX
    e["source_path"] = f
    e["source_n"] = i
    e.write_image(out_hdf, i)
    if (i + 1) % 100 == 0:
        print(f"  {i+1}/{len(mrc_files)}")

print(f"Wrote {len(mrc_files)} particles → {out_hdf}")

lst_path = "ptcls.lst"
lst = LSXFile(lst_path, False)
for i in range(len(mrc_files)):
    lst.write(-1, i, out_hdf)
lst.close()
print(f"Wrote particle list → {lst_path}")

print("Computing initial reference (simple average)...")
avgr = Averagers.get("mean")
for i in range(len(mrc_files)):
    avgr.add_image(EMData(out_hdf, i))
avg = avgr.finish()
avg["apix_x"] = avg["apix_y"] = avg["apix_z"] = APIX
avg.write_image("initial_ref.hdf", 0)
print("Wrote initial_ref.hdf")
print("\nData ingestion complete.")
