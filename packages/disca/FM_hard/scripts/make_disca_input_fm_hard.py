#!/usr/bin/env python3
"""
make_disca_input_fm_hard.py — create DISCA input pickle for FM_hard.

Reads 813 subtomograms (96^3 at 13.33 A/px), downsamples to 32^3 (DISCA
native size), normalises, and writes disca_input_motor_hard.pickle to
~/Research/disca_work/.

Format: {'vs': {stem: {'v': ndarray(32,32,32), 'm': None, 'id': stem}}}

Usage:  conda run -n eman2 python3 packages/disca/FM_hard/scripts/make_disca_input_fm_hard.py
"""
import os, csv, pickle
import numpy as np, mrcfile
from scipy.ndimage import zoom

ALN_DIR  = os.path.expanduser(
    "~/Research/synthetic_sta/motor_hard/subtomos/merged_ABC_full")
LABELS   = os.path.join(ALN_DIR, "labels.csv")
OUT_PATH = os.path.expanduser("~/Research/disca_work/disca_input_motor_hard.pickle")

TARGET = 32

rows  = list(csv.DictReader(open(LABELS)))
files = [r["file"] for r in rows]
n = len(files)
print(f"Building DISCA input: {n} particles, 96->32^3")

vs = {}
for i, fname in enumerate(files):
    fpath = os.path.join(ALN_DIR, fname)
    with mrcfile.open(fpath, permissive=True) as m:
        vol = m.data.astype(np.float32)
    scale = TARGET / vol.shape[0]
    vol32 = zoom(vol, scale, order=1).astype(np.float32)
    mu, std = vol32.mean(), vol32.std()
    if std < 1e-9: std = 1.0
    vol32 = (vol32 - mu) / std
    stem = os.path.splitext(fname)[0]
    vs[stem] = {'v': vol32, 'm': None, 'id': stem}
    if (i+1) % 100 == 0:
        print(f"  {i+1}/{n}")

data = {'vs': vs}
with open(OUT_PATH, 'wb') as f:
    pickle.dump(data, f, protocol=4)
print(f"Wrote {OUT_PATH}  ({n} particles, 32^3)")
