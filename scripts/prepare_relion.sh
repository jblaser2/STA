#!/bin/bash

set -e

INPUT_DIR="subtomos_mrc"
OUTPUT_DIR="outputs/relion"
SUBTOMO_DIR="$OUTPUT_DIR/subtomos"

mkdir -p "$SUBTOMO_DIR"

cp "$INPUT_DIR"/*.mrc "$SUBTOMO_DIR"/

STAR_FILE="$OUTPUT_DIR/particles.star"

cat > "$STAR_FILE" << EOF

data_

loop_
_rlnImageName #1
EOF

counter=1

for f in $(ls "$SUBTOMO_DIR"/*.mrc | sort); do
    base=$(basename "$f")
    echo "$counter@$SUBTOMO_DIR/$base" >> "$STAR_FILE"
    counter=$((counter + 1))
done

echo "RELION STAR file written to: $STAR_FILE"
