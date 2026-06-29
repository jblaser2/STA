#!/usr/bin/env python3
"""
build_labels_matrix.py — aggregate per-package T4P class assignments into a
single particle × package labels matrix.

Outputs outputs/benchmark/T4P_labels_matrix.csv with one row per particle
that appears in at least one package, columns:
  particle, dynamo_k2, peet_k3, pytom_k2, protomo_k2, consensus_score

consensus_score = number of packages that give the same assignment as Dynamo
after Hungarian label alignment (0 if particle absent from Dynamo).

Junk particles (PEET class 3, ProTomo already excluded at extraction) are
represented as NaN in the matrix.

Usage (run from repo root):
  python3 scripts/analysis/build_labels_matrix.py
  python3 scripts/analysis/build_labels_matrix.py --out path/to/output.csv
"""
import argparse
import os
import numpy as np
import pandas as pd
from pathlib import Path
from scipy.optimize import linear_sum_assignment

REPO = Path(__file__).resolve().parents[2]

SOURCES = [
    dict(
        col="dynamo_k2",
        csv=REPO / "packages/dynamo/T4P/results/dynamo_final_results/class_assignments.csv",
        id_col="particle",
        label_col="class",
        junk_classes=set(),
    ),
    dict(
        col="peet_k3",
        csv=REPO / "packages/peet/T4P/results/peet_final_class_assignments_v2.csv",
        id_col="particle",
        label_col="class",
        junk_classes={3},
    ),
    dict(
        col="pytom_k2",
        csv=REPO / "results/pytom_v2mask_k2.csv",
        id_col="file",
        label_col="pred_label",
        junk_classes=set(),
    ),
    dict(
        col="protomo_k2",
        csv=REPO / "results/protomo_T4P_k2.csv",
        id_col="file",
        label_col="pred_label",
        junk_classes=set(),
    ),
]


def load_series(src: dict) -> pd.Series:
    df = pd.read_csv(src["csv"])
    df[src["id_col"]] = df[src["id_col"]].apply(lambda x: os.path.basename(str(x)))
    s = df.set_index(src["id_col"])[src["label_col"]].astype(float)
    if src["junk_classes"]:
        s[s.isin(src["junk_classes"])] = np.nan
    return s


def align_to_ref(ref: pd.Series, other: pd.Series) -> pd.Series:
    """Return `other` with labels permuted to maximally agree with `ref`."""
    shared = ref.dropna().index.intersection(other.dropna().index)
    if len(shared) == 0:
        return other.copy()
    vR = ref.loc[shared].astype(int).values
    vO = other.loc[shared].astype(int).values
    clsR = sorted(np.unique(vR))
    clsO = sorted(np.unique(vO))
    cm = np.zeros((len(clsR), len(clsO)), dtype=int)
    for r, o in zip(vR, vO):
        cm[clsR.index(r), clsO.index(o)] += 1
    row_ind, col_ind = linear_sum_assignment(-cm)
    mapping = {float(clsO[col_ind[i]]): float(clsR[row_ind[i]])
               for i in range(len(row_ind))}
    return other.map(mapping)


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out",
                    default=str(REPO / "outputs/benchmark/T4P_labels_matrix.csv"),
                    help="Output CSV path")
    args = ap.parse_args()

    series = {}
    for src in SOURCES:
        if not Path(src["csv"]).exists():
            print(f"WARNING: missing {src['col']}: {src['csv']}")
            continue
        series[src["col"]] = load_series(src)

    # Build full index (union of all particles)
    all_particles = pd.Index([])
    for s in series.values():
        all_particles = all_particles.union(s.index)

    mat = pd.DataFrame(index=all_particles)
    mat.index.name = "particle"
    for col, s in series.items():
        mat[col] = s.reindex(all_particles)

    # Consensus score: align each non-reference package to Dynamo, count agreements
    ref_col = "dynamo_k2"
    if ref_col in mat.columns:
        ref = mat[ref_col]
        non_ref_cols = [c for c in mat.columns if c != ref_col]
        aligned = {ref_col: ref}
        for col in non_ref_cols:
            aligned[col] = align_to_ref(ref, mat[col])

        consensus = pd.Series(0, index=mat.index)
        for col in non_ref_cols:
            # +1 where both are non-NaN and agree
            agree = (
                aligned[ref_col].notna() &
                aligned[col].notna() &
                (aligned[ref_col] == aligned[col])
            )
            consensus += agree.astype(int)
        mat["consensus_score"] = consensus
    else:
        print("WARNING: dynamo_k2 not found; skipping consensus score")

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    mat.to_csv(out)
    print(f"Wrote {len(mat)} particles × {len(mat.columns)} columns -> {out}")

    if "consensus_score" in mat.columns:
        print("\nConsensus score distribution (vs Dynamo, max=3 other packages):")
        for v in sorted(mat["consensus_score"].dropna().unique()):
            n = int((mat["consensus_score"] == v).sum())
            print(f"  {int(v)}/3 packages agree: {n} particles")
        n_all = int((mat["consensus_score"] == 3).sum())
        print(f"\n  High-consensus core (3/3 agree with Dynamo): {n_all} particles")


if __name__ == "__main__":
    main()
