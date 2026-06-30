#!/usr/bin/env python3
"""Build PEET inputs for the T3SS injectisome dataset.

415 particles (48³, 13.33 Å/px): 215 class_B + 120 class_C + 80 junk.
Junk protocol: all 415 included; k=2 evaluation ignores junk assignment.

Outputs under ~/Research/peet/t3ss/results/:
  stacked.mrc
  stacked.mod
  t3ss_MOTL_Tom1_Iter1.csv
  t3ss_MOTL_Tom1_Iter2.csv
  t3ss.prm
"""
import os, csv, subprocess
import numpy as np
import mrcfile

PARTICLES = os.path.expanduser(
    "~/Research/synthetic_sta/injectisome/subtomos/merged_BC_t3ss")
MASK      = os.path.expanduser(
    "~/Research/synthetic_sta/injectisome/maps/mask_t3ss.mrc")
OUT_DIR   = os.path.expanduser("~/Research/peet/t3ss/results")
os.makedirs(OUT_DIR, exist_ok=True)

BOX  = 48
APIX = 13.33
MOTL_HEADER = (
    "CCC,reserved,reserved,pIndex,wedgeWT,adjCCC,NA,NA,NA,NA,"
    "xOffset,yOffset,zOffset,NA,NA,oldClass,EulerZ(1),EulerZ(3),EulerX(2),class,"
    "CREATED WITH PEET Version 1.18.2"
)

rows = list(csv.DictReader(open(os.path.join(PARTICLES, "labels.csv"))))
n = len(rows)
print(f"Particles: {n}  (junk included for blind run)")

# ── Stack ────────────────────────────────────────────────────────────────────
print(f"Stacking {n} × {BOX}³ volumes …")
vols = []
for row in rows:
    with mrcfile.open(os.path.join(PARTICLES, row["file"]),
                      mode='r', permissive=True) as m:
        vol = m.data.astype(np.float64)
    mu, std = vol.mean(), vol.std()
    if std < 1e-9: std = 1.0
    vols.append(((vol - mu) / std).astype(np.float32))

stacked = np.concatenate(vols, axis=0)
stacked_mrc = os.path.join(OUT_DIR, "stacked.mrc")
with mrcfile.new(stacked_mrc, overwrite=True) as m:
    m.set_data(stacked); m.voxel_size = APIX
print(f"  stacked.mrc  shape={stacked.shape}")
del stacked

# ── IMOD model ───────────────────────────────────────────────────────────────
coords_txt = "/tmp/peet_t3ss_coords.txt"
model_path = os.path.join(OUT_DIR, "stacked.mod")
half = BOX // 2  # 24
with open(coords_txt, "w") as f:
    for i in range(n):
        z = half + i * BOX
        f.write(f"{i+1} {half} {half} {z}\n")
subprocess.check_call(["point2model", "-scat",
    "-input", coords_txt, "-image", stacked_mrc, "-output", model_path])
print(f"  stacked.mod")

# ── MOTLs ────────────────────────────────────────────────────────────────────
motl1 = os.path.join(OUT_DIR, "t3ss_MOTL_Tom1_Iter1.csv")
motl2 = os.path.join(OUT_DIR, "t3ss_MOTL_Tom1_Iter2.csv")
with open(motl1, "w") as f:
    f.write(MOTL_HEADER + "\n")
    for i in range(n):
        f.write(f"0,0,0,{i+1},0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1\n")
with open(motl2, "w") as f:
    f.write(MOTL_HEADER + "\n")
    for i in range(n):
        f.write(f"0.500000,0,0,{i+1},0,0.500000,0,0,0,0,0,0,0,0,0,0,0,0,0,1\n")
print(f"  MOTLs written")

# ── PRM ─────────────────────────────────────────────────────────────────────
ref_path = os.path.join(OUT_DIR, "t3ss_initial_ref.mrc")
prm_path = os.path.join(OUT_DIR, "t3ss.prm")
prm = f"""# PEET parameter file — T3SS injectisome dataset
# {n} particles (48³, {APIX} A/px), all 415 including junk
# pcaFnParticleMask: cylinder R=20 covering IM ring Y=[2,27]
# outsideMaskRadius=22 (≈ half-box margin)

fnVolume = {{'{stacked_mrc}'}}
fnModParticle = {{'{model_path}'}}
initMOTL = {{'{motl1}'}}
fnOutput = 't3ss'
szVol = [{BOX} {BOX} {BOX}]

maskType = 'sphere'
insideMaskRadius = 0
outsideMaskRadius = 22

pcaFnParticleMask = '{MASK}'

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
print(f"  t3ss.prm")
print(f"\nDone. Run:")
print(f"  cd {OUT_DIR}")
print(f"  source ~/Applications/IMOD-linux.sh && source ~/Applications/Particle.sh")
print(f"  averageAll {prm_path} 1 2>&1 | tee averageAll_t3ss.log")
print(f"  cp t3ss_avg_Tom1_Iter1.mrc {ref_path}")
print(f"  pca {prm_path} 1 {n} {ref_path} 1 2>&1 | tee pca_t3ss.log")
