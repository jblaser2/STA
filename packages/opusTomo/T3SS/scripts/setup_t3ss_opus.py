#!/usr/bin/env python3
"""Create STAR file + dummy CTF for T3SS OPUS-TOMO run (415 particles, 48^3)."""
import glob, os, sys

PARTICLE_DIR = os.path.expanduser(
    "~/Research/synthetic_sta/injectisome/subtomos/merged_BC_t3ss")
DUMMY_CTF = os.path.join(PARTICLE_DIR, "dummy_ctf.star")

if len(sys.argv) < 2:
    sys.exit("Usage: setup_t3ss_opus.py <PROJ_DIR>")

PROJ_DIR = sys.argv[1]
os.makedirs(PROJ_DIR, exist_ok=True)
OUT_STAR = os.path.join(PROJ_DIR, "particles.star")

dummy_ctf_content = """\
data_images

loop_
_rlnAngleTilt
_rlnDefocusU
_rlnVoltage
_rlnSphericalAberration
_rlnAmplitudeContrast
_rlnCtfBfactor
_rlnCtfScalefactor
0.0\t20000.0\t300.0\t2.7\t0.07\t0.0\t1.0

"""
with open(DUMMY_CTF, "w") as f:
    f.write(dummy_ctf_content)
print(f"Wrote dummy CTF STAR -> {DUMMY_CTF}")

mrc_paths = sorted(glob.glob(os.path.join(PARTICLE_DIR, "subtomo_*.mrc")))
if not mrc_paths:
    sys.exit(f"ERROR: No subtomo_*.mrc in {PARTICLE_DIR}")

lines = [
    "data_", "loop_",
    "_rlnImageName", "_rlnCtfImage",
    "_rlnAngleRot", "_rlnAngleTilt", "_rlnAnglePsi",
    "_rlnOriginX", "_rlnOriginY", "_rlnOriginZ",
    "_rlnMicrographName",
]
for p in mrc_paths:
    basename = os.path.basename(p)
    stem     = os.path.splitext(basename)[0]
    lines.append(f"{basename}\tdummy_ctf.mrc\t0.0\t0.0\t0.0\t0.0\t0.0\t0.0\t{stem}")

with open(OUT_STAR, "w") as f:
    f.write("\n".join(lines) + "\n")
print(f"Wrote {len(mrc_paths)} particles -> {OUT_STAR}")
