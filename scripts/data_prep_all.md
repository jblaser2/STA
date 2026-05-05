# Cryo-ET Subvolume Conversion / Preparation Scripts

These scripts assume you already have:

* aligned subtomogram `.mrc` volumes
* one particle per file
* all files in a single directory
* consistent voxel dimensions

The goal is to convert or organize the subtomograms into formats expected by:

* RELION
* EMAN2
* Dynamo
* STOPGAP
* emClarity
* Warp/M

---

# Directory Assumptions

Example directory structure:

```text
project/
├── subtomos_mrc/
│   ├── particle_0001.mrc
│   ├── particle_0002.mrc
│   └── ...
├── scripts/
└── outputs/
```

Set:

```bash
INPUT_DIR=subtomos_mrc
```

---

# 1. RELION Preparation

RELION subtomogram classification typically expects:

* particles listed in a STAR file
* subtomograms usually stored as `.mrc` or `.mrcs`
* optional optics group metadata

## Output

```text
outputs/relion/
├── particles.star
└── subtomos/
```

## Script: prepare_relion.sh

```bash
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
```

## Notes

RELION may additionally require:

* `_rlnOriginXAngst`
* `_rlnOriginYAngst`
* `_rlnOriginZAngst`
* Euler angles
* optics groups

for refinement workflows.

For pure classification benchmarking, this minimal STAR file is often sufficient as a starting point.

---

# 2. EMAN2 Preparation

EMAN2 commonly uses:

* `.hdf` stacks
* or `.lst` particle lists

## Output

```text
outputs/eman2/
├── particles.hdf
└── particles.lst
```

## Script: prepare_eman2.sh

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

## Required Environment

```bash
conda activate eman2
```

---

# 3. Dynamo Preparation

Dynamo commonly expects:

* `.em` volumes
* particle table (`.tbl`)

## Output

```text
outputs/dynamo/
├── particles/
├── particles.tbl
```

## Script: prepare_dynamo.sh

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

## Notes

`dmconvert` is part of Dynamo.

You may instead use:

```bash
dynamo xform
```

or MATLAB-based conversion routines.

---

# 4. STOPGAP Preparation

STOPGAP generally expects:

* particle stacks
* motive lists
* metadata STAR-like tables

Many workflows directly use MRC stacks.

## Output

```text
outputs/stopgap/
├── particles.mrcs
└── motive_list.star
```

## Script: prepare_stopgap.py

```python
import os
import glob
import mrcfile
import numpy as np

input_dir = "subtomos_mrc"
output_dir = "outputs/stopgap"

os.makedirs(output_dir, exist_ok=True)

files = sorted(glob.glob(os.path.join(input_dir, "*.mrc")))

volumes = []

for f in files:
    with mrcfile.open(f, permissive=True) as m:
        volumes.append(m.data.astype(np.float32))

stack = np.stack(volumes)

stack_path = os.path.join(output_dir, "particles.mrcs")

with mrcfile.new(stack_path, overwrite=True) as m:
    m.set_data(stack)

star_path = os.path.join(output_dir, "motive_list.star")

with open(star_path, "w") as out:
    out.write("data_\n\n")
    out.write("loop_\n")
    out.write("_rlnImageName #1\n")

    for i in range(len(files)):
        out.write(f"{i+1}@particles.mrcs\\n")

print("STOPGAP stack written")
```

## Required Packages

```bash
pip install mrcfile numpy
```

---

# 5. emClarity Preparation

emClarity typically uses:

* particle motive lists (`motl`)
* subtomogram stacks
* tilt-series metadata

Subtomograms are often stored as `.mrc`.

## Output

```text
outputs/emclarity/
├── particles/
└── motl.csv
```

## Script: prepare_emclarity.sh

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

## Notes

Real emClarity workflows normally require:

* tomogram indices
* particle coordinates
* wedge geometry
* alignment transforms

This simplified format is useful for controlled classification comparisons.

---

# 6. Warp / M Preparation

Warp/M often expects:

* particle metadata STAR files
* subtomogram stacks
* normalized voxel sizes

## Output

```text
outputs/warp_m/
├── particles.star
└── subtomos/
```

## Script: prepare_warp_m.sh

```bash
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
```

---

# 7. Optional Normalization Step

Many packages benefit from normalized subtomograms.

## Script: normalize_subtomos.py

```python
import os
import glob
import numpy as np
import mrcfile

input_dir = "subtomos_mrc"
output_dir = "normalized_subtomos"

os.makedirs(output_dir, exist_ok=True)

files = sorted(glob.glob(os.path.join(input_dir, "*.mrc")))

for f in files:

    with mrcfile.open(f, permissive=True) as m:
        data = m.data.astype(np.float32)

    data -= np.mean(data)
    data /= np.std(data)

    out = os.path.join(output_dir, os.path.basename(f))

    with mrcfile.new(out, overwrite=True) as m:
        m.set_data(data)

print("Normalization complete")
```

---

# 8. Optional MRC -> MRCS Stack Conversion

Several packages prefer stack files.

## Script: make_mrcs_stack.py

```python
import os
import glob
import numpy as np
import mrcfile

input_dir = "subtomos_mrc"
output_stack = "particles.mrcs"

files = sorted(glob.glob(os.path.join(input_dir, "*.mrc")))

volumes = []

for f in files:
    with mrcfile.open(f, permissive=True) as m:
        volumes.append(m.data.astype(np.float32))

stack = np.stack(volumes)

with mrcfile.new(output_stack, overwrite=True) as m:
    m.set_data(stack)

print(f"Saved stack with shape {stack.shape}")
```

---

# 9. SLURM Batch Example

## Script: run_conversion.slurm

```bash
#!/bin/bash

#SBATCH --job-name=subtomo_convert
#SBATCH --time=02:00:00
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=32G
#SBATCH --output=convert_%j.out

module load python

source ~/miniconda3/etc/profile.d/conda.sh
conda activate cryoet

python prepare_stopgap.py
```

---

# 10. Recommended Standardized Benchmark Workflow

For fair cross-package classification benchmarking:

1. Normalize all subtomograms
2. Ensure identical voxel sizes
3. Ensure identical box dimensions
4. Use identical particle ordering
5. Avoid package-specific preprocessing initially
6. Export all package inputs from the same master dataset
7. Keep a master particle index mapping

Recommended master files:

```text
master_particles.csv
master_particles.star
master_particles.json
```

containing:

* particle ID
* source filename
* class label
* coordinates
* alignment transform
* voxel size
* tomogram ID

This prevents indexing mismatches across packages.

