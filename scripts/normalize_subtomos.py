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
