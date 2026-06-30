#!/usr/bin/env python3
"""Setup PyTom particle list + mask for FM_hard (813 particles, 96^3, k=3).
Run with pytom_env."""
import os, sys, glob
sys.path.insert(0, os.path.expanduser("~/Research/pytom"))

STA_DIR  = os.path.expanduser("~/Research/STA")
DATA_DIR = os.path.expanduser(
    "~/Research/synthetic_sta/motor_hard/subtomos/merged_ABC_full")
MASK_MRC = os.path.expanduser(
    "~/Research/synthetic_sta/motor_hard/maps/diff_mask_hard.mrc")
MASK_EM  = os.path.join(STA_DIR, "packages/PyTom/FM_hard/configs/diff_mask_hard.em")
PL_OUT   = os.path.join(STA_DIR, "packages/PyTom/FM_hard/configs/particle_list_fm_hard.xml")
WEDGE_ANG = 30.0

os.makedirs(os.path.dirname(MASK_EM), exist_ok=True)

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
