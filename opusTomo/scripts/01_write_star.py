#!/usr/bin/env python3
"""Create a RELION 3.0 STAR file from the aligned subtomogram MRCs.

Particles are z-axis aligned with no known in-plane rotation, so all
Euler angles are set to zero. Paths in the STAR are basenames only;
training uses --datadir to locate the files.
"""
import glob, os, sys

PARTICLE_DIR = os.path.expanduser('~/src/particles')
SCRIPT_DIR   = os.path.dirname(os.path.abspath(__file__))
OUT_STAR     = os.path.join(SCRIPT_DIR, 'particles.star')

mrc_paths = sorted(glob.glob(os.path.join(PARTICLE_DIR, 'aligned_tom*.mrc')))
if not mrc_paths:
    sys.exit(f'ERROR: No MRC files found in {PARTICLE_DIR}')

lines = [
    'data_',
    'loop_',
    '_rlnImageName',
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
    lines.append(f'{basename}\t0.0\t0.0\t0.0\t0.0\t0.0\t0.0\t{tomo_name}')

with open(OUT_STAR, 'w') as f:
    f.write('\n'.join(lines) + '\n')

print(f'Wrote {len(mrc_paths)} particles -> {OUT_STAR}')
