#!/usr/bin/env python3
"""
Compute class averages from PEET K-means classification results.

Reads peet_single_MOTL_Tom1_Iter2.csv (updated by usePcaMotiveLists)
and averages the corresponding subtomogram MRC files for each class.

Outputs:
  results/class_1_avg.mrc
  results/class_2_avg.mrc
"""

import os
import glob
import numpy as np
import mrcfile

SUBTOMOS_DIR = os.path.expanduser("~/Research/STA/subtomos_mrc")
RESULTS_DIR  = os.path.expanduser("~/Research/peet/results")
MOTL_PATH    = os.path.join(RESULTS_DIR, "peet_single_MOTL_Tom1_Iter2.csv")

def main():
    # Load sorted subtomogram list (same order used when building stacked MRC)
    files = sorted(glob.glob(os.path.join(SUBTOMOS_DIR, "aligned_*.mrc")))
    assert len(files) == 672, f"Expected 672 MRC files, found {len(files)}"

    # Parse MOTL: pIndex (col 4, 1-indexed) and class (last col)
    classes = {}  # pIndex → class_id
    with open(MOTL_PATH) as f:
        next(f)  # skip header
        for line in f:
            parts = line.strip().split(',')
            pidx  = int(parts[3])
            cls   = int(parts[19])
            classes[pidx] = cls

    assert len(classes) == 672, f"Expected 672 entries, got {len(classes)}"
    class_ids = sorted(set(classes.values()))
    print(f"Classes: {class_ids}")
    for c in class_ids:
        count = sum(1 for v in classes.values() if v == c)
        print(f"  Class {c}: {count} particles")

    # Compute per-class averages
    for cls in class_ids:
        indices = [i for i in range(672) if classes.get(i + 1) == cls]
        print(f"\nAveraging {len(indices)} particles for class {cls}...")
        acc = None
        for i in indices:
            with mrcfile.open(files[i], mode='r', permissive=True) as m:
                vol = m.data.astype(np.float64)
                if acc is None:
                    acc = np.zeros_like(vol)
                acc += vol

        avg = (acc / len(indices)).astype(np.float32)
        out_path = os.path.join(RESULTS_DIR, f"class_{cls}_avg.mrc")
        with mrcfile.new(out_path, overwrite=True) as m:
            m.set_data(avg)
            m.voxel_size = 13.328
        print(f"  Wrote {out_path}")

    print("\nDone. Load class_1_avg.mrc and class_2_avg.mrc in 3dmod to compare.")

if __name__ == "__main__":
    main()
