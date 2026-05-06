import os
import re
import numpy as np
import mrcfile
import argparse

def parse_filename(fname):
    """
    Extract tomogram ID and particle ID from filename:
    aligned_tomXXX_PYYYY.mrc
    """
    match = re.search(r'tom(\d+)_P(\d+)', fname)
    if not match:
        raise ValueError(f"Filename does not match expected pattern: {fname}")
    
    tomo_id = int(match.group(1))
    particle_id = int(match.group(2))
    return tomo_id, particle_id


def generate_motl(input_dir, output_file, box_size=None, seed=42):
    np.random.seed(seed)

    files = sorted([f for f in os.listdir(input_dir) if f.endswith('.mrc')])
    n = len(files)

    if n == 0:
        raise ValueError("No .mrc files found")

    print(f"Found {n} subvolumes")

    motl = np.zeros((n, 20), dtype=np.float32)

    for i, fname in enumerate(files):
        path = os.path.join(input_dir, fname)

        # Extract IDs from filename
        tomo_id, particle_local_id = parse_filename(fname)

        # Get box size
        if box_size is None:
            with mrcfile.open(path, permissive=True) as mrc:
                bx, by, bz = mrc.data.shape
        else:
            bx = by = bz = box_size

        cx, cy, cz = bx / 2, by / 2, bz / 2

        # Fill MOTL row
        motl[i, 0] = 0                     # score
        motl[i, 1] = i + 1                 # global particle ID
        motl[i, 2] = tomo_id              # tomogram ID (REAL now)
        motl[i, 3] = 1                    # class

        motl[i, 4] = cx                   # x
        motl[i, 5] = cy                   # y
        motl[i, 6] = cz                   # z

        motl[i, 7] = 0                    # shift x
        motl[i, 8] = 0                    # shift y
        motl[i, 9] = 0                    # shift z

        motl[i, 10] = 0                   # phi
        motl[i, 11] = 0                   # psi
        motl[i, 12] = 0                   # theta

        # columns 13–18 left as 0

        motl[i, 19] = np.random.randint(1, 3)  # halfset (1 or 2)

    np.savetxt(output_file, motl, fmt="%.6f")

    print(f"MOTL saved to: {output_file}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate MOTL from aligned_tomXXX_PYYYY.mrc files")
    parser.add_argument("--input_dir", required=True, help="Directory with .mrc files")
    parser.add_argument("--output", default="motl.txt", help="Output MOTL file")
    parser.add_argument("--box_size", type=int, default=None, help="Override box size")
    parser.add_argument("--seed", type=int, default=42)

    args = parser.parse_args()

    generate_motl(args.input_dir, args.output, args.box_size, args.seed)
