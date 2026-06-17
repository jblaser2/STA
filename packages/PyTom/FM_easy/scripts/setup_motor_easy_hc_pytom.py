#!/usr/bin/env python3
"""Setup PyTom particle list + mask for the REDESIGNED 2-class hc FM_easy (542 A/C).
Run with pytom_env."""
import os, sys, glob
sys.path.insert(0, os.path.expanduser("~/Research/pytom"))

STA_DIR   = os.path.expanduser("~/Research/STA")
DATA_DIR  = os.path.expanduser("~/Research/synthetic_sta/motor_easy/hc_test_x6/subtomos/merged_AC_full")
MASK_MRC  = os.path.join(STA_DIR, "packages/dynamo/dynamo_outputs/easy_pair_AC_hc/diff_sphere_r23_y55.mrc")
MASK_EM   = os.path.join(STA_DIR, "packages/PyTom/FM_easy/configs/motor_easy_hc_mask.em")
PL_OUT    = os.path.join(STA_DIR, "packages/PyTom/FM_easy/configs/particle_list_motor_easy_hc.xml")
WEDGE_ANG = 30.0  # ±60° tilt range

from pytom.lib.pytom_volume import read
from pytom.basic.structures import ParticleList, Particle, SingleTiltWedge

print(f"Converting mask: {MASK_MRC} -> {MASK_EM}")
read(MASK_MRC).write(MASK_EM)

mrc_files = sorted(glob.glob(os.path.join(DATA_DIR, "subtomo_*.mrc")))
print(f"Building ParticleList: {len(mrc_files)} particles")
wedge = SingleTiltWedge(WEDGE_ANG)
pl = ParticleList()
for fpath in mrc_files:
    pl.append(Particle(fpath))
pl.setWedgeAllParticles(wedge)
pl.toXMLFile(PL_OUT)
print(f"Saved: {PL_OUT}")
