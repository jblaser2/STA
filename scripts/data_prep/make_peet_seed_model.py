#!/usr/bin/env python3
"""
make_peet_seed_model.py — create a RELION model.star that seeds 3D classification
from PEET class average MRCs so RELION starts from structurally distinct references.

Usage:
  python3 scripts/data_prep/make_peet_seed_model.py \
      --refs /path/class_1.mrc /path/class_2.mrc \
      --out  outputs/relion/Class3D/peet_seed_model.star
"""
import argparse
import os


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--refs", nargs="+", required=True,
                    help="Per-class reference MRC paths (one per class, in class order)")
    ap.add_argument("--out", required=True, help="Output model.star path")
    args = ap.parse_args()

    K = len(args.refs)
    dist = 1.0 / K

    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)

    lines = [
        "# version 50001",
        "",
        "data_model_classes",
        "",
        "loop_",
        "_rlnReferenceImage #1",
        "_rlnClassDistribution #2",
        "_rlnAccuracyRotations #3",
        "_rlnAccuracyTranslationsAngst #4",
        "_rlnEstimatedResolution #5",
        "_rlnOverallFourierCompleteness #6",
    ]
    for ref in args.refs:
        lines.append(f"{os.path.abspath(ref)}  {dist:.6f}  999.000000  999.000000  999.000000  0.000000")
    lines.append("")

    with open(args.out, "w") as f:
        f.write("\n".join(lines))

    print(f"Wrote {K}-class seed model.star -> {args.out}")
    for i, ref in enumerate(args.refs, 1):
        print(f"  class {i}: {ref}")


if __name__ == "__main__":
    main()
