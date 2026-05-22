# emClarity Preparation

emClarity typically uses:

- particle motive lists (motl)
- subtomogram stacks
- tilt-series metadata

Subtomograms are often stored as `.mrc`.

### Output
```
outputs/emclarity/
├── particles/
└── motl.csv
```

### Script: prepare_emclarity.sh

```bash
#!/bin/bash

set -e

INPUT_DIR="subtomos_mrc"
OUTPUT_DIR="outputs/emclarity"
PARTICLE_DIR="$OUTPUT_DIR/particles"

mkdir -p "$PARTICLE_DIR"

cp "$INPUT_DIR"/*.mrc "$PARTICLE_DIR"/

MOTL="$OUTPUT_DIR/motl.csv"
rm -f "$MOTL"

counter=1

for f in $(ls "$PARTICLE_DIR"/*.mrc | sort); do

    base=$(basename "$f")

    echo "$counter,0,0,0,0,0,0,$base" >> "$MOTL"

    counter=$((counter + 1))
done

echo "emClarity MOTL created: $MOTL"
```

### Notes
Real emClarity workflows normally require:

tomogram indices
particle coordinates
wedge geometry
alignment transforms

This simplified format is useful for controlled classification comparisons.

