#!/usr/bin/env python3
"""
setup_t3ss_relion.py — build RELION inputs for T3SS injectisome classification.
Creates: particles.star, wedge_ctf.mrc, initial_ref.mrc, solvent_mask.mrc

Run from STA repo root:
  conda run -n eman2 python3 packages/relion/T3SS/scripts/setup_t3ss_relion.py
"""
import os, csv, glob, numpy as np, mrcfile
from pathlib import Path

PARTICLES_DIR = Path.home() / "Research/synthetic_sta/injectisome/subtomos/merged_BC_t3ss"
MASK_MRC      = Path.home() / "Research/synthetic_sta/injectisome/maps/mask_t3ss.mrc"
OUT_DIR       = Path("outputs/T3SS/relion")
BOX           = 48
APIX          = 13.33
TILT_MIN      = -60.0
TILT_MAX      =  60.0
TILT_STEP     =   3.0

OUT_DIR.mkdir(parents=True, exist_ok=True)
(OUT_DIR / "ctf").mkdir(exist_ok=True)

# 1. Wedge CTF file (binary: 1 inside tilt range, 0 in missing wedge)
def make_wedge(box, tilt_min, tilt_max):
    """Binary wedge weight in Fourier space. Tilt axis = Y."""
    center = box // 2
    freq = np.fft.fftshift(np.fft.fftfreq(box))
    kx, ky, kz = np.meshgrid(freq, freq, freq, indexing='ij')
    # angle of each Fourier voxel from tilt axis (Y-axis)
    r = np.sqrt(kx**2 + kz**2)
    with np.errstate(invalid='ignore', divide='ignore'):
        tilt_angle = np.where(r > 0, np.degrees(np.arctan2(kx, kz)), 0.0)
    wedge = (tilt_angle >= tilt_min) & (tilt_angle <= tilt_max)
    return wedge.astype(np.float32)

ctf_out = OUT_DIR / "ctf" / "wedge_ctf.mrc"
if not ctf_out.exists():
    wedge = make_wedge(BOX, TILT_MIN, TILT_MAX)
    with mrcfile.new(str(ctf_out), overwrite=True) as m:
        m.set_data(wedge)
        m.voxel_size = APIX
    print(f"wedge_ctf.mrc: shape={wedge.shape} nonzero={wedge.sum():.0f}")
else:
    print("wedge_ctf.mrc: exists, skipping")

# 2. Global average reference
ref_out = OUT_DIR / "initial_ref.mrc"
files = sorted(PARTICLES_DIR.glob("subtomo_*.mrc"))
print(f"Particles: {len(files)}")
if not ref_out.exists():
    acc = None
    for f in files:
        with mrcfile.open(str(f), permissive=True) as m:
            v = m.data.astype(np.float32)
        acc = v.copy() if acc is None else acc + v
    avg = acc / len(files)
    with mrcfile.new(str(ref_out), overwrite=True) as m:
        m.set_data(avg)
        m.voxel_size = APIX
    print(f"initial_ref.mrc: shape={avg.shape}")
else:
    print("initial_ref.mrc: exists, skipping")

# 3. Solvent mask (from classification mask, dilated slightly)
mask_out = OUT_DIR / "solvent_mask.mrc"
if not mask_out.exists():
    with mrcfile.open(str(MASK_MRC), permissive=True) as m:
        mask = m.data.astype(np.float32)
    # RELION needs smooth-edged mask: use the existing mask as-is (already soft)
    with mrcfile.new(str(mask_out), overwrite=True) as m:
        m.set_data(mask)
        m.voxel_size = APIX
    print(f"solvent_mask.mrc: shape={mask.shape} nonzero={(mask>0.1).sum()}")
else:
    print("solvent_mask.mrc: exists, skipping")

# 4. STAR file with all 415 particles
star_out = OUT_DIR / "particles_wedge.star"
ctf_abs = str(ctf_out.resolve())

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

print(f"particles_wedge.star: {len(files)} particles -> {star_out}")
print("Setup complete.")
