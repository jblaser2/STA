#!/bin/bash

set -e

INPUT_DIR="subtomos_mrc"
OUTPUT_DIR="outputs/warp_m"
SUBTOMO_DIR="$OUTPUT_DIR/subtomos"

mkdir -p "$SUBTOMO_DIR"

cp "$INPUT_DIR"/*.mrc "$SUBTOMO_DIR"/

STAR="$OUTPUT_DIR/particles.star"

cat > "$STAR" << EOF

data_particles

loop_
_rlnImageName #1
EOF

counter=1

for f in $(ls "$SUBTOMO_DIR"/*.mrc | sort); do

    base=$(basename "$f")

    echo "$counter@$SUBTOMO_DIR/$base" >> "$STAR"

    counter=$((counter + 1))
done

echo "Warp/M STAR file created"
