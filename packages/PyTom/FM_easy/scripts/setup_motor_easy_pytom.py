#!/usr/bin/env python3
"""Setup PyTom particle list + mask for motor_easy. Run with pytom_env."""
import os, sys, glob
sys.path.insert(0, os.path.expanduser("~/Research/pytom"))

STA_DIR   = os.path.expanduser("~/Research/STA")
DATA_DIR  = os.path.expanduser("~/Research/synthetic_sta/motor_easy/production/subtomos/merged_all_aln")
MASK_MRC  = os.path.join(STA_DIR, "outputs/relion_motor_easy/solvent_mask.mrc")
MASK_EM   = os.path.join(STA_DIR, "packages/PyTom/motor_easy_mask.em")
PL_OUT    = os.path.join(STA_DIR, "packages/PyTom/particle_list_motor_easy.xml")
WEDGE_ANG = 30.0  # ±60° tilt range

from pytom.lib.pytom_volume import read, vol
from pytom.basic.structures import ParticleList, Particle, SingleTiltWedge

# 1. Convert MRC mask → EM
print(f"Converting mask: {MASK_MRC} -> {MASK_EM}")
mask_vol = read(MASK_MRC)
mask_vol.write(MASK_EM)
print(f"  Done: mask converted")

# 2. Build particle list
mrc_files = sorted(glob.glob(os.path.join(DATA_DIR, "subtomo_*.mrc")))
print(f"\nBuilding ParticleList: {len(mrc_files)} particles")
wedge = SingleTiltWedge(WEDGE_ANG)
pl = ParticleList()
for fpath in mrc_files:
    p = Particle(fpath)
    pl.append(p)
pl.setWedgeAllParticles(wedge)
pl.toXMLFile(PL_OUT)
print(f"  Saved: {PL_OUT}")
print(f"\nDone. Ready for auto_focus_classify.")
