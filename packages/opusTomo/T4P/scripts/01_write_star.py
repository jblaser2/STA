#!/usr/bin/env python3
"""Create a RELION 3.0 STAR file from the aligned subtomogram MRCs, and
write a dummy per-tilt CTF STAR file required by OPUS-ET's dataset loader.

_rlnCtfImage is unconditionally read by dataset.load_subtomos() regardless
of --ctfalpha/--ctfbeta. It expects a per-particle STAR file (extension
changed from .mrc to .star) with a data_images block of per-tilt CTF params.
We create one shared dummy_ctf.star in the particle datadir and point every
particle at it. With --ctfalpha 0 --ctfbeta 0 these values are never applied.
"""
import glob, os, sys

PARTICLE_DIR = os.path.expanduser('~/src/particles')
SCRIPT_DIR   = os.path.dirname(os.path.abspath(__file__))
OUT_STAR     = os.path.join(SCRIPT_DIR, 'particles.star')
DUMMY_CTF    = os.path.join(PARTICLE_DIR, 'dummy_ctf.star')

# --- Write dummy CTF STAR into the particle datadir ---
# get_3dctfs() changes _rlnCtfImage extension from .mrc -> .star and reads
# this file. prefix_paths() resolves it as datadir/basename(value).star.
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
with open(DUMMY_CTF, 'w') as f:
    f.write(dummy_ctf_content)
print(f'Wrote dummy CTF STAR -> {DUMMY_CTF}')

# --- Write particles STAR ---
mrc_paths = sorted(glob.glob(os.path.join(PARTICLE_DIR, 'aligned_tom*.mrc')))
if not mrc_paths:
    sys.exit(f'ERROR: No MRC files found in {PARTICLE_DIR}')

lines = [
    'data_',
    'loop_',
    '_rlnImageName',
    '_rlnCtfImage',
    '_rlnAngleRot',
    '_rlnAngleTilt',
    '_rlnAnglePsi',
    '_rlnOriginX',
    '_rlnOriginY',
    '_rlnOriginZ',
    '_rlnMicrographName',
]

for p in mrc_paths:
    basename  = os.path.basename(p)                 # aligned_tom100_P0001.mrc
    tomo_name = '_'.join(basename.split('_')[:2])   # aligned_tom100
    # _rlnCtfImage = dummy_ctf.mrc -> get_3dctfs looks for datadir/dummy_ctf.star
    lines.append(f'{basename}\tdummy_ctf.mrc\t0.0\t0.0\t0.0\t0.0\t0.0\t0.0\t{tomo_name}')

with open(OUT_STAR, 'w') as f:
    f.write('\n'.join(lines) + '\n')

print(f'Wrote {len(mrc_paths)} particles -> {OUT_STAR}')
