#!/usr/bin/env python3
"""
build_relion_star.py — enrich the minimal particle list into a RELION-3.1+ style
two-block star (data_optics + data_particles) suitable for classic 3D-subtomogram
Class3D on the already-reconstructed, pre-aligned T4P subtomograms.

Why two blocks: RELION >=3.1 reads is_3D from the optics block's
rlnImageDimensionality (see RELION src/exp_model.cpp:888). With --ctf and 3D data,
relion_refine REQUIRES rlnCtfImage per particle (src/ml_optimiser.cpp:10343), so we
point every particle at ONE shared 3D CTF model (no tilt series -> no per-particle
CTF). Two variants are written for the wedge-vs-uniform comparison.

Angles/origins are all zero: the subtomograms are already aligned and centered
(see outputs/motl.txt). Paths are written relative to the STA project root, so run
relion_refine from /home/jblaser2/Research/STA.

Run in an env with numpy + mrcfile (e.g. relion-5.0 or eman2).
"""
import argparse
import os
import re
import mrcfile


def detect_box_pixel(mrc_path):
    with mrcfile.open(mrc_path, permissive=True) as mrc:
        box = int(mrc.data.shape[-1])
        vox = float(mrc.voxel_size.x) if mrc.voxel_size.x > 0 else None
    return box, vox


OPTICS_HEADER = """
# RELION optics group: placeholder CTF params (no real per-particle CTF for these
# already-reconstructed subtomograms). rlnImageDimensionality 3 triggers 3D mode.
data_optics

loop_
_rlnOpticsGroup #1
_rlnOpticsGroupName #2
_rlnImagePixelSize #3
_rlnImageSize #4
_rlnImageDimensionality #5
_rlnVoltage #6
_rlnSphericalAberration #7
_rlnAmplitudeContrast #8
1 opticsGroup1 {pix:.4f} {box} 3 300.0 2.7 0.1
"""

PARTICLES_HEADER = """
data_particles

loop_
_rlnImageName #1
_rlnCtfImage #2
_rlnOpticsGroup #3
_rlnAngleRot #4
_rlnAngleTilt #5
_rlnAnglePsi #6
_rlnOriginXAngst #7
_rlnOriginYAngst #8
_rlnOriginZAngst #9
"""


def write_star(out_path, mrc_files, subtomo_dir, ctf_image, pix, box):
    with open(out_path, "w") as f:
        f.write(OPTICS_HEADER.format(pix=pix, box=box))
        f.write(PARTICLES_HEADER)
        for fname in mrc_files:
            img = os.path.join(subtomo_dir, fname)
            f.write(f"{img} {ctf_image} 1 0.0 0.0 0.0 0.0 0.0 0.0\n")
    print(f"wrote {out_path}  ({len(mrc_files)} particles, ctf={ctf_image})")


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--subtomo-dir", default="subtomos_mrc",
                    help="dir of aligned_*.mrc, relative to project root")
    ap.add_argument("--outdir", default="outputs/relion")
    ap.add_argument("--wedge-ctf", default="outputs/relion/ctf/wedge_ctf.mrc")
    ap.add_argument("--uniform-ctf", default="outputs/relion/ctf/uniform_ctf.mrc")
    ap.add_argument("--pixel-size", type=float, default=None,
                    help="override; default autodetect from first mrc")
    args = ap.parse_args()

    mrc_files = sorted(f for f in os.listdir(args.subtomo_dir) if f.endswith(".mrc"))
    if not mrc_files:
        raise SystemExit(f"no .mrc in {args.subtomo_dir}")

    box, vox = detect_box_pixel(os.path.join(args.subtomo_dir, mrc_files[0]))
    pix = args.pixel_size or vox or 13.328
    print(f"{len(mrc_files)} particles  box={box}  pixel={pix:.4f} A")

    os.makedirs(args.outdir, exist_ok=True)
    write_star(os.path.join(args.outdir, "particles_wedge.star"),
               mrc_files, args.subtomo_dir, args.wedge_ctf, pix, box)
    write_star(os.path.join(args.outdir, "particles_uniform.star"),
               mrc_files, args.subtomo_dir, args.uniform_ctf, pix, box)


if __name__ == "__main__":
    main()
