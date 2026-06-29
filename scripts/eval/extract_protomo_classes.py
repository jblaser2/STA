#!/usr/bin/env python3
"""
extract_protomo_classes.py — extract per-particle class assignments from a
ProTomo .i3i class file and write predictions CSV (file, pred_label).

ProTomo stores assignments in a binary .i3i file. We read them with:
  tomoinfo -cls <file.i3i>
which outputs one line per particle:  "[ k ] idx class"
where idx is 0-based and class is an integer (2 = junk by default).

The particle filename list is built by listing the stacks/ directory
(sorted alphabetically — same order ProTomo uses).

Usage (run from repo root or anywhere):
  python3 scripts/eval/extract_protomo_classes.py \
      --i3i   ~/Research/protomo/process/cycle-000/t4p-000-class.i3i \
      --stacks ~/Research/protomo/prepare/stacks \
      --out   results/protomo_T4P_k2.csv

Junk class (default 2) is excluded from the output CSV.
"""
import argparse
import os
import subprocess
import csv
from pathlib import Path


def get_filenames(stacks_dir: Path) -> list[str]:
    names = sorted(
        f for f in os.listdir(stacks_dir)
        if f.endswith(".mrc")
    )
    return names


def parse_class_i3i(i3i_path: Path) -> dict[int, int]:
    result = subprocess.run(
        ["tomoinfo", "-cls", str(i3i_path)],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        raise RuntimeError(f"tomoinfo failed: {result.stderr}")

    assignments = {}
    for line in result.stdout.splitlines():
        parts = line.strip().split()
        # expected: [ k ] idx class
        if len(parts) >= 5 and parts[0] == "[" and parts[2] == "]":
            idx = int(parts[3])
            cls = int(parts[4])
            assignments[idx] = cls
    return assignments


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--i3i", required=True,
                    help="ProTomo class .i3i file (e.g. cycle-000/t4p-000-class.i3i)")
    ap.add_argument("--stacks", required=True,
                    help="Directory containing particle .mrc files (sorted = ProTomo index order)")
    ap.add_argument("--out", required=True, help="Output predictions CSV (file, pred_label)")
    ap.add_argument("--junk-class", type=int, default=2,
                    help="Class label to exclude as junk (default: 2)")
    args = ap.parse_args()

    i3i_path = Path(args.i3i)
    stacks_dir = Path(args.stacks)

    filenames = get_filenames(stacks_dir)
    assignments = parse_class_i3i(i3i_path)

    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)

    written = junk_skipped = missing = 0
    with open(args.out, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["file", "pred_label"])
        for idx, fname in enumerate(filenames):
            cls = assignments.get(idx)
            if cls is None:
                missing += 1
                continue
            if cls == args.junk_class:
                junk_skipped += 1
                continue
            w.writerow([fname, cls])
            written += 1

    print(f"Wrote {written} particles -> {args.out}")
    print(f"  Junk excluded (class {args.junk_class}): {junk_skipped}")
    if missing:
        print(f"  WARNING: {missing} particles had no assignment in .i3i")


if __name__ == "__main__":
    main()
