#!/usr/bin/env python3
"""
setup_fm_hard_relion.py — build RELION inputs for FM_hard classification.
Creates: particles.star, wedge_ctf.mrc, initial_ref.mrc, solvent_mask.mrc
Run from STA repo root:
  conda run -n eman2 python3 packages/relion/FM_hard/scripts/setup_fm_hard_relion.py
"""
import os, csv, glob
import numpy as np, mrcfile
from pathlib import Path

PARTICLES_DIR = Path.home() / "Research/synthetic_sta/motor_hard/subtomos/merged_ABC_full"
MASK_MRC      = Path.home() / "Research/synthetic_sta/motor_hard/maps/diff_mask_hard.mrc"
OUT_DIR       = Path("outputs/FM_hard/relion")
BOX, APIX     = 96, 13.329

OUT_DIR.mkdir(parents=True, exist_ok=True)
(OUT_DIR / "ctf").mkdir(exist_ok=True)

def make_wedge(box, tmin=-60.0, tmax=60.0):
    freq = np.fft.fftshift(np.fft.fftfreq(box))
    kx, ky, kz = np.meshgrid(freq, freq, freq, indexing='ij')
    r = np.sqrt(kx**2 + kz**2)
    with np.errstate(invalid='ignore', divide='ignore'):
        tilt = np.where(r>0, np.degrees(np.arctan2(kx,kz)), 0.0)
    return ((tilt>=tmin) & (tilt<=tmax)).astype(np.float32)

ctf_out = OUT_DIR / "ctf" / "wedge_ctf.mrc"
if not ctf_out.exists():
    with mrcfile.new(str(ctf_out), overwrite=True) as m:
        m.set_data(make_wedge(BOX)); m.voxel_size = APIX
    print(f"wedge_ctf.mrc created")
else:
    print("wedge_ctf.mrc: exists")

files = sorted(PARTICLES_DIR.glob("subtomo_*.mrc"))
print(f"Particles: {len(files)}")

ref_out = OUT_DIR / "initial_ref.mrc"
if not ref_out.exists():
    acc = None
    for f in files:
        with mrcfile.open(str(f), permissive=True) as m:
            v = m.data.astype(np.float32)
        acc = v.copy() if acc is None else acc + v
    with mrcfile.new(str(ref_out), overwrite=True) as m:
        m.set_data(acc/len(files)); m.voxel_size = APIX
    print(f"initial_ref.mrc created")
else:
    print("initial_ref.mrc: exists")

mask_out = OUT_DIR / "solvent_mask.mrc"
if not mask_out.exists():
    with mrcfile.open(str(MASK_MRC), permissive=True) as m:
        mask = m.data.astype(np.float32)
    with mrcfile.new(str(mask_out), overwrite=True) as m:
        m.set_data(mask); m.voxel_size = APIX
    print(f"solvent_mask.mrc: {(mask>0.1).sum()} nonzero")
else:
    print("solvent_mask.mrc: exists")

ctf_abs = str(ctf_out.resolve())
star_out = OUT_DIR / "particles.star"
with open(star_out, 'w') as f:
    f.write("data_optics\n\nloop_\n")
    f.write("_rlnOpticsGroup #1\n_rlnOpticsGroupName #2\n")
    f.write("_rlnImagePixelSize #3\n_rlnImageSize #4\n_rlnImageDimensionality #5\n")
    f.write("_rlnVoltage #6\n_rlnSphericalAberration #7\n_rlnAmplitudeContrast #8\n")
    f.write(f"1 opticsGroup1 {APIX:.4f} {BOX} 3 300.0 2.7 0.1\n\n")
    f.write("data_particles\n\nloop_\n")
    f.write("_rlnImageName #1\n_rlnCtfImage #2\n_rlnOpticsGroup #3\n")
    f.write("_rlnAngleRot #4\n_rlnAngleTilt #5\n_rlnAnglePsi #6\n")
    f.write("_rlnOriginXAngst #7\n_rlnOriginYAngst #8\n_rlnOriginZAngst #9\n")
    for fp in files:
        f.write(f"{fp.resolve()} {ctf_abs} 1 0.0 0.0 0.0 0.0 0.0 0.0\n")
print(f"particles.star: {len(files)} particles -> {star_out}")
print("Setup complete.")
