#!/bin/bash
# run_relion_motor_easy_v2.sh — RELION Class3D on motor_easy synthetic data.
# v2: seed each of K=3 classes from GT class averages (breaks symmetry properly);
#     use focused off-center solvent mask (r=32 px, center Y-10); skip_align retained
#     since particles are pre-aligned to canonical orientation.
# Run from ~/Research/STA project root.
set -e

RELION=/home/jblaser2/relion-install/bin/relion_refine
REFS=outputs/relion_motor_easy/class_refs.star
MASK=outputs/relion_motor_easy/solvent_mask.mrc
OUTROOT=outputs/relion_motor_easy/Class3D
ITER="${ITER:-25}"

STAR="outputs/relion_motor_easy/particles_wedge.star"
OUT="${OUTROOT}/k3_wedge_v2"
mkdir -p "$OUT"
echo "=== $(date +%H:%M:%S)  RELION Class3D motor_easy  K=3  v2 (GT-seeded) ==="

"$RELION" \
  --i "$STAR" --ref "$REFS" --o "$OUT/run" \
  --K 3 --iter "$ITER" --tau2_fudge 4 --ini_high 60 \
  --solvent_mask "$MASK" --flatten_solvent --zero_mask \
  --skip_align \
  --sym C1 --ctf --skip_subtomo_multi --pad 2 --norm --scale \
  --dont_combine_weights_via_disc --j 8 --gpu "" \
  > "$OUT/run.log" 2>&1
echo "=== DONE $(date +%H:%M:%S) (exit $?) -> $OUT ==="
