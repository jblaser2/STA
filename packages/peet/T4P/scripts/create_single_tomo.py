#!/usr/bin/env python3
"""
Stack 672 pre-aligned subtomograms into a single MRC for PEET single-tomogram analysis.

Creates:
  results/stacked_all.mrc       - Z-stacked volume (80 x 80 x 53760)
  results/stacked_all.mod       - IMOD model with 672 particle positions
  results/peet_single_MOTL_Tom1_Iter1.csv  - initMOTL (zero rotations)
  results/peet_single_MOTL_Tom1_Iter2.csv  - Iter2 with real CCC values
  peet_project_single.prm       - PEET parameter file for single-tomogram run
"""

import os
import glob
import subprocess
import numpy as np
import mrcfile

SUBTOMOS_DIR = os.path.expanduser("~/Research/STA/subtomos_mrc")
RESULTS_DIR  = os.path.expanduser("~/Research/peet/results")
PEET_DIR     = os.path.expanduser("~/Research/peet")

MOTL_HEADER = (
    "CCC,reserved,reserved,pIndex,wedgeWT,adjCCC,NA,NA,NA,NA,"
    "xOffset,yOffset,zOffset,NA,NA,oldClass,EulerZ(1),EulerZ(3),EulerX(2),class,"
    "CREATED WITH PEET Version 1.18.2 11-Sept-2025"
)

def main():
    # ── 1. Load subtomograms in sorted order ─────────────────────────────────
    files = sorted(glob.glob(os.path.join(SUBTOMOS_DIR, "aligned_*.mrc")))
    assert len(files) == 672, f"Expected 672 MRC files, found {len(files)}"
    print(f"Found {len(files)} subtomograms.")

    # ── 2. Stack along Z with per-particle z-score normalization ─────────────
    # Z-score normalization: subtract per-particle mean and divide by std.
    # This removes brightness variation and makes PCA focus on structure,
    # equivalent to using Pearson cross-correlation as the distance metric.
    print("Stacking volumes along Z with z-score normalization (may take ~30 s)...")
    vols = []
    for f in files:
        with mrcfile.open(f, mode='r', permissive=True) as m:
            vol = m.data.astype(np.float64)   # (80, 80, 80)
        mu  = vol.mean()
        std = vol.std()
        if std < 1e-9:
            std = 1.0
        vols.append(((vol - mu) / std).astype(np.float32))

    stacked = np.concatenate(vols, axis=0)            # (53760, 80, 80)
    assert stacked.shape == (672 * 80, 80, 80), stacked.shape

    stacked_mrc = os.path.join(RESULTS_DIR, "stacked_all.mrc")
    with mrcfile.new(stacked_mrc, overwrite=True) as m:
        m.set_data(stacked)
        m.voxel_size = 13.328
    print(f"Wrote {stacked_mrc}  shape={stacked.shape}")
    del stacked  # free memory

    # ── 3. Create IMOD model: 672 contours, 1 point each ─────────────────────
    coords_txt = "/tmp/peet_stacked_coords.txt"
    model_path = os.path.join(RESULTS_DIR, "stacked_all.mod")
    with open(coords_txt, "w") as f:
        for i in range(672):
            # contour#  X   Y   Z (0-indexed pixel coordinates)
            z = 40 + i * 80
            f.write(f"{i+1} 40 40 {z}\n")

    # Contour numbers in coords_txt cause point2model to auto-create 672 contours.
    # -number cannot be combined with explicit contour numbers.
    subprocess.check_call([
        "point2model",
        "-scat",                # scattered point type
        "-input", coords_txt,
        "-image", stacked_mrc,
        "-output", model_path,
    ])
    print(f"Wrote {model_path}")

    # ── 4. Get CCC values from existing TEMP files ────────────────────────────
    # TEMP files are named peet_run_TEMP_Tom{i}_Iter2_P1-1.csv and ordered
    # to match the same sorted order as the MRC files.
    temp_files = sorted(glob.glob(
        os.path.join(RESULTS_DIR, "peet_run_TEMP_Tom*_Iter2_P1-1.csv")
    ))
    if len(temp_files) != 672:
        print(f"WARNING: Found {len(temp_files)} TEMP files (expected 672). "
              "Using CCC=0 for missing ones.")

    ccc_map = {}  # index → CCC  (1-indexed)
    for i, tf in enumerate(temp_files):
        with open(tf) as fh:
            lines = fh.readlines()
        row = lines[1].strip().split(',')
        ccc_map[i + 1] = float(row[0])

    cccs = [ccc_map.get(i + 1, 0.0) for i in range(672)]
    print(f"CCC range: {min(cccs):.4f} – {max(cccs):.4f}")

    # ── 5. Write Iter1 MOTL (zero rotations / offsets) ───────────────────────
    iter1_path = os.path.join(RESULTS_DIR, "peet_single_MOTL_Tom1_Iter1.csv")
    with open(iter1_path, "w") as f:
        f.write(MOTL_HEADER + "\n")
        for i in range(672):
            f.write(f"0,0,0,{i+1},0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0\n")
    print(f"Wrote {iter1_path}")

    # ── 6. Write Iter2 MOTL (real CCC from previous alignSubset) ─────────────
    iter2_path = os.path.join(RESULTS_DIR, "peet_single_MOTL_Tom1_Iter2.csv")
    with open(iter2_path, "w") as f:
        f.write(MOTL_HEADER + "\n")
        for i, ccc in enumerate(cccs):
            f.write(f"{ccc:.6f},0,0,{i+1},0,{ccc:.6f},0,0,0,0,0,0,0,0,0,0,0,0,0,0\n")
    print(f"Wrote {iter2_path}")

    # ── 7. Write peet_project_single.prm ─────────────────────────────────────
    prm_path = os.path.join(PEET_DIR, "peet_project_single.prm")
    prm = f"""# PEET parameter file — single stacked tomogram
# 672 pre-aligned subtomograms stacked into one MRC along Z
# Particles at (40, 40, 40+i*80) for i=0..671

fnVolume = {{'{stacked_mrc}'}}
fnModParticle = {{'{model_path}'}}

initMOTL = {{'{iter1_path}'}}

fnOutput = 'peet_single'
szVol = [78 78 78]

maskType = 'sphere'
insideMaskRadius = 0
outsideMaskRadius = 9

yaxisType = 0
sampleSphere = 'none'

dPhi   = {{[0], [0]}}
dTheta = {{[0], [0]}}
dPsi   = {{[0], [0]}}
searchRadius = {{[0], [0]}}

lowCutoff = {{[0.05 0.05], [0.05 0.05]}}
hiCutoff  = {{[0.45 0.05], [0.45 0.05]}}

flgFairReference = 0
reference = 'reference_initial.mrc'

refThreshold  = [672, 672]
refFlagAllTom = 1

tiltRange = {{}}
flgWedgeWeight = 0
nWeightGroup = 8

lstThresholds = [672]
lstFlagAllTom = 1

pixelSpacing = 13.328
CCMode      = 0
flgAbsValue = 1
particlePerCPU = 8
debugLevel = 1
nIter = 2
"""
    with open(prm_path, "w") as f:
        f.write(prm)
    print(f"Wrote {prm_path}")
    print("\nDone. Next steps:")
    print("  cd ~/Research/peet/results")
    print("  source ~/Applications/IMOD-linux.sh && source ~/Applications/Particle.sh")
    print("  averageAll ../peet_project_single.prm 1 2>&1 | tee averageAll_single.log")
    print("  pca ../peet_project_single.prm 1 672 reference_initial.mrc 1 2>&1 | tee pca_single.log")

if __name__ == "__main__":
    main()
