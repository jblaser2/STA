#!/usr/bin/env python3
"""
make_stack_fm_hard.py — prepare PEET inputs for FM_hard (813 particles, 96^3, 3 classes).

Creates under ~/Research/peet/motor_hard/results/:
  stacked.mrc          Z-stacked volume (96 x 96 x 78048 for 813 particles)
  stacked.mod          IMOD model with 813 particle positions
  motor_hard_MOTL_Tom1_Iter1.csv  initMOTL (identity angles, CCC=0)
  motor_hard_MOTL_Tom1_Iter2.csv  initMOTL (CCC=0.5, required by PEET pca)
  motor_hard.prm       PEET parameter file

Run with:  conda run -n eman2 python3 packages/peet/FM_hard/scripts/make_stack_fm_hard.py
"""
import os, csv, subprocess
import numpy as np, mrcfile

ALN_DIR   = os.path.expanduser(
    "~/Research/synthetic_sta/motor_hard/subtomos/merged_ABC_full")
LABELS_CSV = os.path.join(ALN_DIR, "labels.csv")
MASK_MRC   = os.path.expanduser(
    "~/Research/synthetic_sta/motor_hard/maps/diff_mask_hard.mrc")
OUT_DIR   = os.path.expanduser("~/Research/peet/motor_hard/results")
os.makedirs(OUT_DIR, exist_ok=True)

BOX  = 96
APIX = 13.329

MOTL_HEADER = (
    "CCC,reserved,reserved,pIndex,wedgeWT,adjCCC,NA,NA,NA,NA,"
    "xOffset,yOffset,zOffset,NA,NA,oldClass,EulerZ(1),EulerZ(3),EulerX(2),class,"
    "CREATED WITH PEET Version 1.18.2"
)

def main():
    # 1. Sorted file list
    files = [r["file"] for r in csv.DictReader(open(LABELS_CSV))]
    n = len(files)
    print(f"Found {n} particles")

    # 2. Stack along Z (z-score normalised)
    stacked_mrc = os.path.join(OUT_DIR, "stacked.mrc")
    if os.path.exists(stacked_mrc):
        print(f"stacked.mrc exists, skipping stack build")
    else:
        print(f"Stacking {n} volumes ({BOX}^3) along Z …")
        stack = np.zeros((n * BOX, BOX, BOX), dtype=np.float32)
        for idx, fname in enumerate(files):
            with mrcfile.open(os.path.join(ALN_DIR, fname), permissive=True) as m:
                vol = m.data.astype(np.float64)
            mu, std = vol.mean(), vol.std()
            if std < 1e-9: std = 1.0
            stack[idx*BOX:(idx+1)*BOX] = ((vol - mu) / std).astype(np.float32)
        with mrcfile.new(stacked_mrc, overwrite=True) as m:
            m.set_data(stack)
            m.voxel_size = APIX
        print(f"Wrote {stacked_mrc}  shape={stack.shape}")

    # 3. IMOD model
    half = BOX // 2
    model_path = os.path.join(OUT_DIR, "stacked.mod")
    coords_txt = os.path.join(OUT_DIR, "_coords.txt")
    with open(coords_txt, "w") as f:
        for i in range(n):
            z = half + i * BOX
            f.write(f"{i+1} {half} {half} {z}\n")
    subprocess.run([
        "point2model", "-scat",
        "-input",  coords_txt,
        "-image",  stacked_mrc,
        "-output", model_path,
    ], check=True)
    print(f"Wrote {model_path}")

    # 4. MOTLs
    motl_path  = os.path.join(OUT_DIR, "motor_hard_MOTL_Tom1_Iter1.csv")
    motl2_path = os.path.join(OUT_DIR, "motor_hard_MOTL_Tom1_Iter2.csv")
    with open(motl_path, "w") as f:
        f.write(MOTL_HEADER + "\n")
        for i in range(n):
            f.write(f"0,0,0,{i+1},0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1\n")
    with open(motl2_path, "w") as f:
        f.write(MOTL_HEADER + "\n")
        for i in range(n):
            f.write(f"0.500000,0,0,{i+1},0,0.500000,0,0,0,0,0,0,0,0,0,0,0,0,0,1\n")
    print(f"Wrote {motl_path}, {motl2_path}")

    # 5. PRM file
    ref_path = os.path.join(OUT_DIR, "motor_hard_initial_ref.mrc")
    prm_path = os.path.join(OUT_DIR, "motor_hard.prm")
    prm = f"""# PEET parameter file — FM_hard synthetic data
# {n} GT-aligned subtomograms (96^3, 13.33 A/px) stacked along Z
# 3 classes: base / basal_body / mature (271 each)
# Identity MOTL — all euler angles = 0 (particles already GT-aligned)
# pcaFnParticleMask: diff_mask_hard.mrc (3-class diff mask, 5.5% of box)
# tiltRange [-60,60] + flgWedgeWeight=1 — native WMD in Fourier space

fnVolume = {{'{stacked_mrc}'}}
fnModParticle = {{'{model_path}'}}

initMOTL = {{'{motl_path}'}}

fnOutput = 'motor_hard'
szVol = [96 96 96]

maskType = 'sphere'
insideMaskRadius = 0
outsideMaskRadius = 44

pcaFnParticleMask = '{MASK_MRC}'

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
    print(f"\nNext steps:")
    print(f"  cd {OUT_DIR}")
    print(f"  source ~/Applications/IMOD-linux.sh && source ~/Applications/Particle.sh")
    print(f"  averageAll {prm_path} 1 2>&1 | tee averageAll_motor_hard.log")
    print(f"  # Copy avg to ref:")
    print(f"  cp motor_hard_AvgVol_1P{n}.mrc {ref_path}   (or glob motor_hard_Avg*P{n}.mrc)")
    print(f"  pca {prm_path} 1 {n} {ref_path} 1 2>&1 | tee pca_motor_hard.log")

if __name__ == "__main__":
    main()
