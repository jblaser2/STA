#!/usr/bin/env python3
"""
motor_easy_stack.py — prepare PEET inputs for motor_easy synthetic data.

Creates under ~/Research/peet/motor_easy/results/:
  stacked.mrc               Z-stacked volume (96 x 96 x 60864 for 634 particles)
  stacked.mod               IMOD model with 634 particle positions
  motor_easy_MOTL_Tom1_Iter1.csv  initMOTL (identity angles)

Also writes:
  ~/Research/STA/peet/motor_easy.prm   PEET parameter file

Run with:  conda run -n relion-5.0 python3 peet/motor_easy_stack.py
(any env with mrcfile + numpy + subprocess)
"""
import os
import csv
import subprocess
import numpy as np
import mrcfile

ALN_DIR   = os.path.expanduser(
    "~/Research/synthetic_sta/motor_easy/production/subtomos/merged_all_aln")
LABELS_CSV = os.path.join(ALN_DIR, "labels.csv")

OUT_DIR   = os.path.expanduser("~/Research/peet/motor_easy/results")
PEET_DIR  = os.path.expanduser("~/Research/STA/peet")

os.makedirs(OUT_DIR, exist_ok=True)

MOTL_HEADER = (
    "CCC,reserved,reserved,pIndex,wedgeWT,adjCCC,NA,NA,NA,NA,"
    "xOffset,yOffset,zOffset,NA,NA,oldClass,EulerZ(1),EulerZ(3),EulerX(2),class,"
    "CREATED WITH PEET Version 1.18.2"
)

BOX   = 96
APIX  = 13.329


def main():
    # ── 1. Get sorted file list from labels.csv ───────────────────────────────
    files = []
    with open(LABELS_CSV) as f:
        for row in csv.DictReader(f):
            files.append(row["file"])
    n = len(files)
    print(f"Found {n} particles from labels.csv")

    # ── 2. Stack along Z with z-score normalization ───────────────────────────
    print(f"Stacking {n} volumes ({BOX}³ each) along Z …")
    vols = []
    for fname in files:
        with mrcfile.open(os.path.join(ALN_DIR, fname), mode='r',
                          permissive=True) as m:
            vol = m.data.astype(np.float64)
        mu  = vol.mean()
        std = vol.std()
        if std < 1e-9:
            std = 1.0
        vols.append(((vol - mu) / std).astype(np.float32))

    stacked = np.concatenate(vols, axis=0)
    expected_shape = (n * BOX, BOX, BOX)
    assert stacked.shape == expected_shape, f"{stacked.shape} != {expected_shape}"

    stacked_mrc = os.path.join(OUT_DIR, "stacked.mrc")
    with mrcfile.new(stacked_mrc, overwrite=True) as m:
        m.set_data(stacked)
        m.voxel_size = APIX
    print(f"Wrote {stacked_mrc}  shape={stacked.shape}")
    del stacked

    # ── 3. IMOD model: n contours, 1 point each at box center ────────────────
    coords_txt = "/tmp/peet_motor_easy_coords.txt"
    model_path = os.path.join(OUT_DIR, "stacked.mod")
    half = BOX // 2  # 48
    with open(coords_txt, "w") as f:
        for i in range(n):
            z = half + i * BOX
            f.write(f"{i+1} {half} {half} {z}\n")

    subprocess.check_call([
        "point2model", "-scat",
        "-input",  coords_txt,
        "-image",  stacked_mrc,
        "-output", model_path,
    ])
    print(f"Wrote {model_path}")

    # ── 4. Initial MOTLs (identity rotations, class=1) ────────────────────────
    # PEET convention: averageAll/pca with iterationNumber=1 reads Iter2 MOTL.
    # Create both; Iter2 is identical to Iter1 (no alignment needed — particles
    # are already GT-aligned).
    motl_path = os.path.join(OUT_DIR, "motor_easy_MOTL_Tom1_Iter1.csv")
    motl2_path = os.path.join(OUT_DIR, "motor_easy_MOTL_Tom1_Iter2.csv")
    # Iter1: zero CCC (initial state before any alignment)
    with open(motl_path, "w") as f:
        f.write(MOTL_HEADER + "\n")
        for i in range(n):
            f.write(f"0,0,0,{i+1},0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1\n")
    # Iter2: CCC=0.5 so PEET includes all particles (CCC=0 causes PEET to skip them)
    with open(motl2_path, "w") as f:
        f.write(MOTL_HEADER + "\n")
        for i in range(n):
            f.write(f"0.500000,0,0,{i+1},0,0.500000,0,0,0,0,0,0,0,0,0,0,0,0,0,1\n")
    print(f"Wrote {motl_path}")
    print(f"Wrote {motl2_path}")

    # ── 5. Write PEET prm ─────────────────────────────────────────────────────
    # outsideMaskRadius 11 px ≈ 147 Å (analogous to 9 px for T4P 80³ box)
    # szVol 92: 2 px margin from 96³ box to avoid edge artifacts
    ref_path = os.path.join(OUT_DIR, "motor_easy_initial_ref.mrc")
    prm_path = os.path.join(PEET_DIR, "motor_easy.prm")
    prm = f"""# PEET parameter file — motor_easy synthetic data
# {n} GT-aligned subtomograms (96^3, 13.33 A/px) stacked along Z
# Particles at ({half}, {half}, {half}+i*{BOX}) for i=0..{n-1}
# Identity MOTL — all euler angles = 0 (particles already GT-aligned)
# tiltRange [-60,60] + flgWedgeWeight=1 — native WMD in Fourier space

fnVolume = {{'{stacked_mrc}'}}
fnModParticle = {{'{model_path}'}}

initMOTL = {{'{motl_path}'}}

fnOutput = 'motor_easy'
szVol = [92 92 92]

maskType = 'sphere'
insideMaskRadius = 0
outsideMaskRadius = 11

yaxisType = 0
sampleSphere = 'none'

dPhi   = {{[0], [0]}}
dTheta = {{[0], [0]}}
dPsi   = {{[0], [0]}}
searchRadius = {{[0], [0]}}

lowCutoff = {{[0.05 0.05], [0.05 0.05]}}
hiCutoff  = {{[0.45 0.05], [0.45 0.05]}}

flgFairReference = 0
reference = '{ref_path}'

refThreshold  = [{n}, {n}]
refFlagAllTom = 1

tiltRange = {{[-60, 60]}}
flgWedgeWeight = 1
nWeightGroup = 8

lstThresholds = [{n}]
lstFlagAllTom = 1

pixelSpacing = {APIX}
CCMode      = 0
flgAbsValue = 1
particlePerCPU = 8
debugLevel = 1
nIter = 2
"""
    with open(prm_path, "w") as f:
        f.write(prm)
    print(f"Wrote {prm_path}")

    print(f"\nDone. Next steps:")
    print(f"  cd {OUT_DIR}")
    print(f"  source ~/Applications/IMOD-linux.sh && source ~/Applications/Particle.sh")
    print(f"  # Compute initial reference:")
    print(f"  averageAll {prm_path} 1 2>&1 | tee averageAll_motor_easy.log")
    print(f"  # NOTE: averageAll outputs motor_easy_avg_Tom1_Iter1.mrc")
    print(f"  # Copy it to the reference path expected by pca:")
    print(f"  cp motor_easy_avg_Tom1_Iter1.mrc {ref_path}")
    print(f"  # Run PCA:")
    print(f"  pca {prm_path} 1 {n} {ref_path} 1 2>&1 | tee pca_motor_easy.log")


if __name__ == "__main__":
    main()
