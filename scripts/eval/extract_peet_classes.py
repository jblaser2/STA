#!/usr/bin/env python3
"""
extract_peet_classes.py — extract per-particle class assignments from a PEET
MOTL CSV and write predictions.csv (file, pred_label).

PEET MOTL column layout (1-indexed as in PEET docs):
  col 4  = pIndex (particle index, 1-based)
  col 20 = class assignment

Particle ordering must match the order of files in --labels-csv (the GT labels
file from merged_all_aln/, which lists subtomos in sort order).

Usage:
  python3 scripts/eval/extract_peet_classes.py \
    --motl ~/Research/peet/motor_easy/results/motor_easy_MOTL_Tom1_Iter2.csv \
    --labels ~/Research/synthetic_sta/motor_easy/production/subtomos/merged_all_aln/labels.csv \
    --out outputs/peet_motor_easy/predictions_k2_iter2.csv
"""
import argparse
import os
import csv


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--motl", required=True,
                    help="PEET MOTL CSV (e.g. motor_easy_MOTL_Tom1_Iter2.csv)")
    ap.add_argument("--labels", required=True,
                    help="GT labels CSV (file,label,...) in particle sort order")
    ap.add_argument("--out", required=True, help="Output predictions CSV")
    args = ap.parse_args()

    # Read GT labels to get sorted file list
    gt_files = []
    with open(args.labels) as f:
        for row in csv.DictReader(f):
            gt_files.append(os.path.basename(row["file"]))

    # Read MOTL; pIndex (col 4, 0-indexed col 3) maps to particle order
    # class is col 20 (0-indexed col 19)
    class_by_pidx = {}
    with open(args.motl) as f:
        reader = csv.reader(f)
        header = next(reader)  # skip header line
        for row in reader:
            if len(row) < 20:
                continue
            try:
                pidx = int(float(row[3]))    # pIndex (1-based)
                cls  = int(float(row[19]))   # class
                class_by_pidx[pidx] = cls
            except (ValueError, IndexError):
                continue

    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    written = 0
    missing = 0
    with open(args.out, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["file", "pred_label"])
        for i, fname in enumerate(gt_files):
            pidx = i + 1  # PEET is 1-based
            cls  = class_by_pidx.get(pidx)
            if cls is None:
                missing += 1
                continue
            w.writerow([fname, cls])
            written += 1

    if missing:
        print(f"WARNING: {missing} particles not found in MOTL")
    print(f"Wrote {written} predictions -> {args.out}")


if __name__ == "__main__":
    main()
