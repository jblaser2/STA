# Dynamo Preparation

Dynamo commonly expects:

- .em volumes
- particle table (.tbl)

### Output
```
outputs/dynamo/
├── particles/
├── particles.tbl
```
### Script: prepare_dynamo.sh
```bash
#!/bin/bash

set -e

INPUT_DIR="subtomos_mrc"
OUTPUT_DIR="outputs/dynamo"
PARTICLE_DIR="$OUTPUT_DIR/particles"

mkdir -p "$PARTICLE_DIR"

TABLE_FILE="$OUTPUT_DIR/particles.tbl"
rm -f "$TABLE_FILE"

counter=1

for f in $(ls "$INPUT_DIR"/*.mrc | sort); do

    base=$(basename "$f" .mrc)
    out="$PARTICLE_DIR/${base}.em"

    echo "Converting $f -> $out"

    dmconvert "$f" "$out"

    # Minimal Dynamo table row
    # Columns are placeholders for classification benchmarking

    echo "$counter 1 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 $out" >> "$TABLE_FILE"

    counter=$((counter + 1))
done

echo "Dynamo table written to: $TABLE_FILE"
```

### Notes:
`dmconvert` is part of Dynamo.

You may instead use:
```
dynamo xform
```

or MATLAB-based conversion routines.
