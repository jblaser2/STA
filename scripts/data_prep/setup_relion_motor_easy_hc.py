#!/usr/bin/env python3
"""Build all RELION inputs for the REDESIGNED 2-class hc FM_easy (542 A/C):
  - per-class GT averages (A, C) -> class_refs.star  (GT-seeding)
  - wedge_ctf.mrc (96^3, ±60°)
  - particles_wedge.star (542 particles, identity poses)
Run with relion-5.0 env. Solvent mask is built separately by make_motor_easy_mask.py.
"""
import os, csv, numpy as np, mrcfile

ALN = os.path.expanduser("~/Research/synthetic_sta/motor_easy/hc_test_x6/subtomos/merged_AC_full")
OUT = "outputs/FM_easy/relion"
CTF = os.path.join(OUT, "ctf"); os.makedirs(CTF, exist_ok=True)
APIX = 13.329; BOX = 96; TILT = 60.0

rows = list(csv.DictReader(open(os.path.join(ALN, "labels.csv"))))
files = [r["file"] for r in rows]
print(f"{len(files)} particles")

# --- per-class GT averages ---
refs = {}
for cls in ["A", "C"]:
    cfiles = [r["file"] for r in rows if r["label"] == cls]
    acc = None
    for fn in cfiles:
        d = mrcfile.open(os.path.join(ALN, fn), permissive=True).data.astype(np.float64)
        acc = d if acc is None else acc + d
    avg = (acc / len(cfiles)).astype(np.float32)
    rp = os.path.join(OUT, f"ref_class{cls}_hc.mrc")
    with mrcfile.new(rp, overwrite=True) as m:
        m.set_data(avg); m.voxel_size = APIX
    refs[cls] = os.path.abspath(rp)
    print(f"  ref {cls}: {len(cfiles)} particles -> {rp}")

with open(os.path.join(OUT, "class_refs.star"), "w") as f:
    f.write("\ndata_\n\nloop_\n_rlnReferenceImage\n")
    f.write(refs["A"] + "\n" + refs["C"] + "\n")
print("wrote class_refs.star (A,C)")

# --- wedge CTF (centered single-axis Y missing wedge, ±TILT) ---
c = BOX // 2; ax = np.arange(BOX) - c
kz, ky, kx = np.meshgrid(ax, ax, ax, indexing="ij")
phi = np.degrees(np.arctan2(np.abs(kz), np.abs(kx)))
wedge = (phi <= TILT).astype(np.float32); wedge[c, c, c] = 1.0
wpath = os.path.join(CTF, "wedge_ctf.mrc")
with mrcfile.new(wpath, overwrite=True) as m:
    m.set_data(wedge); m.voxel_size = APIX
print(f"wedge_ctf measured_frac={wedge.mean():.3f} -> {wpath}")

# --- particles STAR ---
opt = (f"\ndata_optics\n\nloop_\n_rlnOpticsGroup #1\n_rlnOpticsGroupName #2\n"
       f"_rlnImagePixelSize #3\n_rlnImageSize #4\n_rlnImageDimensionality #5\n"
       f"_rlnVoltage #6\n_rlnSphericalAberration #7\n_rlnAmplitudeContrast #8\n"
       f"1 opticsGroup1 {APIX:.4f} {BOX} 3 300.0 2.7 0.1\n")
parts = ("\ndata_particles\n\nloop_\n_rlnImageName #1\n_rlnCtfImage #2\n_rlnOpticsGroup #3\n"
         "_rlnAngleRot #4\n_rlnAngleTilt #5\n_rlnAnglePsi #6\n"
         "_rlnOriginXAngst #7\n_rlnOriginYAngst #8\n_rlnOriginZAngst #9\n")
star = os.path.join(OUT, "particles_wedge.star")
with open(star, "w") as f:
    f.write(opt); f.write(parts)
    for fn in files:
        f.write(f"{os.path.join(ALN, fn)} {os.path.abspath(wpath)} 1 0.0 0.0 0.0 0.0 0.0 0.0\n")
print(f"wrote {star} ({len(files)} particles)")
