#!/usr/bin/env python3
"""Setup PyTom particle list + mask for T3SS injectisome dataset (415 particles, 48^3).
Run with pytom_env: conda run -n pytom_env python3 setup_t3ss_pytom.py"""
import os, sys, glob
sys.path.insert(0, os.path.expanduser("~/Research/pytom"))

STA_DIR  = os.path.expanduser("~/Research/STA")
DATA_DIR = os.path.expanduser(
    "~/Research/synthetic_sta/injectisome/subtomos/merged_BC_t3ss")
MASK_MRC = os.path.expanduser(
    "~/Research/synthetic_sta/injectisome/maps/mask_t3ss.mrc")
MASK_EM  = os.path.join(STA_DIR, "packages/PyTom/T3SS/configs/mask_t3ss.em")
PL_OUT   = os.path.join(STA_DIR, "packages/PyTom/T3SS/configs/particle_list_t3ss.xml")
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
