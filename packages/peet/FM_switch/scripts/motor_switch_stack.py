#!/usr/bin/env python3
"""
motor_switch_stack.py — prepare PEET inputs for motor_switch 5 Å/px synthetic data.

451 GT-aligned subtomograms (160³, 5 Å/px): 208 CCW + 208 CW + 35 junk.
Particles already pre-aligned to canonical orientation — identity MOTL.

Creates under ~/Research/peet/motor_switch/results/:
  stacked.mrc                        Z-stacked volume (160 x 160 x 72160)
  stacked.mod                        IMOD model with 451 particle positions
  motor_switch_MOTL_Tom1_Iter1.csv   initMOTL (identity angles)
  motor_switch_MOTL_Tom1_Iter2.csv   Iter2 MOTL (CCC=0.5 so PEET includes all)

Also writes:
  ~/Research/STA/packages/peet/FM_switch/configs/motor_switch.prm

Run with:  conda run -n relion-5.0 python3 packages/peet/FM_switch/scripts/motor_switch_stack.py
"""
import os
import csv
import subprocess
import numpy as np
import mrcfile

ALN_DIR   = os.path.expanduser(
    "~/Research/synthetic_sta/motor_switch/production_5apix/subtomos/all_particles_aligned")
LABELS_CSV = os.path.join(ALN_DIR, "labels.csv")

OUT_DIR  = os.path.expanduser("~/Research/peet/motor_switch/results")
PRM_PATH = os.path.expanduser(
    "~/Research/STA/packages/peet/FM_switch/configs/motor_switch.prm")

MASK_PATH = os.path.expanduser(
    "~/Research/STA/outputs/FM_switch/relion/run_r02/solvent_mask.mrc")

os.makedirs(OUT_DIR, exist_ok=True)

MOTL_HEADER = (
    "CCC,reserved,reserved,pIndex,wedgeWT,adjCCC,NA,NA,NA,NA,"
    "xOffset,yOffset,zOffset,NA,NA,oldClass,EulerZ(1),EulerZ(3),EulerX(2),class,"
    "CREATED WITH PEET Version 1.18.2"
)

BOX  = 160
APIX = 5.0


def main():
    files = []
    with open(LABELS_CSV) as f:
        for row in csv.DictReader(f):
            files.append(row["file"])
    n = len(files)
    print(f"Found {n} particles from labels.csv")

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

    coords_txt = "/tmp/peet_motor_switch_coords.txt"
    model_path = os.path.join(OUT_DIR, "stacked.mod")
    half = BOX // 2  # 80
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

    motl_path  = os.path.join(OUT_DIR, "motor_switch_MOTL_Tom1_Iter1.csv")
    motl2_path = os.path.join(OUT_DIR, "motor_switch_MOTL_Tom1_Iter2.csv")
    with open(motl_path, "w") as f:
        f.write(MOTL_HEADER + "\n")
        for i in range(n):
            f.write(f"0,0,0,{i+1},0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1\n")
    with open(motl2_path, "w") as f:
        f.write(MOTL_HEADER + "\n")
        for i in range(n):
            f.write(f"0.500000,0,0,{i+1},0,0.500000,0,0,0,0,0,0,0,0,0,0,0,0,0,1\n")
    print(f"Wrote {motl_path}")
    print(f"Wrote {motl2_path}")

    ref_path = os.path.join(OUT_DIR, "motor_switch_initial_ref.mrc")

    prm = f"""# PEET parameter file — motor_switch 5 A/px synthetic data
# {n} GT-aligned subtomograms (160^3, 5.0 A/px) stacked along Z
# Particles at ({half}, {half}, {half}+i*{BOX}) for i=0..{n-1}
# Identity MOTL — all euler angles = 0 (particles already GT-aligned)
# tiltRange [-60,60] + flgWedgeWeight=1 — native WMD in Fourier space
# pcaFnParticleMask: RELION ellipsoidal solvent mask (r_xz=38, r_y=65 + soft edge)
#   Motor occupies Y:[14:146], XZ:[41:118] in 160^3 box.
# szVol=160 (full box): no alignment search needed.
# outsideMaskRadius=74: full-box sphere for averaging reference computation.

fnVolume = {{'{stacked_mrc}'}}
fnModParticle = {{'{model_path}'}}

initMOTL = {{'{motl_path}'}}

fnOutput = 'motor_switch'
szVol = [{BOX} {BOX} {BOX}]

maskType = 'sphere'
insideMaskRadius = 0
outsideMaskRadius = 74

pcaFnParticleMask = '{MASK_PATH}'

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
    with open(PRM_PATH, "w") as f:
        f.write(prm)
    print(f"Wrote {PRM_PATH}")

    print(f"\nDone. Next steps:")
    print(f"  source ~/Applications/IMOD-linux.sh && source ~/Applications/Particle.sh")
    print(f"  cd {OUT_DIR}")
    print(f"  averageAll {PRM_PATH} 1 2>&1 | tee averageAll_motor_switch.log")
    print(f"  cp motor_switch_avg_Tom1_Iter1.mrc {ref_path}")
    print(f"  pca {PRM_PATH} 1 {n} {ref_path} 1 2>&1 | tee pca_motor_switch.log")


if __name__ == "__main__":
    main()
