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
