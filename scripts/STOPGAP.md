# STOPGAP Preparation

STOPGAP generally expects:

- particle stacks
- motive lists
- metadata STAR-like tables

Many workflows directly use MRC stacks.

### Output
outputs/stopgap/
├── particles.mrcs
└── motive_list.star

### Script: prepare_stopgap.py
```bash
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

### Required Packages
```
pip install mrcfile numpy
```

