#!/usr/bin/env python3
"""
extract_relion_classes.py — extract per-particle class assignments from a RELION
_data.star output file and write predictions.csv (file, pred_label).

Usage:
  python3 scripts/eval/extract_relion_classes.py \
    --star outputs/relion_motor_easy/Class3D/k3_wedge/run_it025_data.star \
    --input-star outputs/relion_motor_easy/particles_wedge.star \
    --out outputs/relion_motor_easy/Class3D/k3_wedge/predictions.csv
"""
import argparse
import os
import csv


def parse_star_particles(path):
    """Return list of dicts for the data_particles block of a RELION star file."""
    rows = []
    in_block = False
    in_loop = False
    headers = []
    with open(path) as f:
        for line in f:
            line = line.rstrip()
            stripped = line.strip()
            if stripped.startswith("data_"):
                in_block = (stripped == "data_particles")
                in_loop = False
                headers = []
                continue
            if not in_block:
                continue
            if stripped == "loop_":
                in_loop = True
                continue
            if not in_loop:
                continue
            if stripped.startswith("_"):
                headers.append(stripped.split()[0])
                continue
            if stripped == "" or stripped.startswith("data_"):
                in_loop = False
                continue
            vals = stripped.split()
            if len(vals) == len(headers):
                rows.append(dict(zip(headers, vals)))
    return rows


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--star", required=True,
                    help="RELION output *_data.star file")
    ap.add_argument("--input-star", required=True,
                    help="Input particles.star (to get original file list order)")
    ap.add_argument("--out", required=True, help="Output predictions CSV")
    args = ap.parse_args()

    in_rows  = parse_star_particles(args.input_star)
    out_rows = parse_star_particles(args.star)

    if not out_rows:
        raise SystemExit(f"No data_particles rows found in {args.star}")

    # Build lookup: rlnImageName → rlnClassNumber from output star
    class_by_img = {r["_rlnImageName"]: r["_rlnClassNumber"] for r in out_rows}

    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    written = 0
    missing = 0
    with open(args.out, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["file", "pred_label"])
        for row in in_rows:
            img  = row["_rlnImageName"]
            cls  = class_by_img.get(img)
            if cls is None:
                missing += 1
                continue
            w.writerow([os.path.basename(img), cls])
            written += 1

    if missing:
        print(f"WARNING: {missing} particles in input star not found in output star")
    print(f"Wrote {written} predictions -> {args.out}")


if __name__ == "__main__":
    main()
