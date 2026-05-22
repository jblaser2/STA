# EMAN2 Preparation

EMAN2 commonly uses:

- .hdf stacks
- or .lst particle lists

### Output
```
outputs/eman2/
├── particles.hdf
└── particles.lst
```

### Script: prepare_eman2.sh
```bash
#!/bin/bash

set -e

INPUT_DIR="subtomos_mrc"
OUTPUT_DIR="outputs/eman2"

mkdir -p "$OUTPUT_DIR"

HDF_STACK="$OUTPUT_DIR/particles.hdf"
LST_FILE="$OUTPUT_DIR/particles.lst"

rm -f "$HDF_STACK"
rm -f "$LST_FILE"

counter=0

for f in $(ls "$INPUT_DIR"/*.mrc | sort); do
    echo "Adding $f"

    e2proc3d.py "$f" "$HDF_STACK" --append

    echo "$counter\t$HDF_STACK" >> "$LST_FILE"

    counter=$((counter + 1))
done

echo "Created:"
echo "  $HDF_STACK"
echo "  $LST_FILE"
```

### Note:
You need to first install the eman2 environment for this to work.
