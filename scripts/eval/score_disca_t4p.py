#!/usr/bin/env python3
"""
score_disca_t4p.py — build DISCA T4P assignment CSVs from the saved label
pickles and report pairwise ARI vs the converging packages (PEET v2, Dynamo,
PyTom).

DISCA stores cluster labels as a plain numpy array whose order matches the
input pickle's `vs` dict insertion order. build_disca_input.py builds that dict
by iterating `sorted(os.listdir(subtomo_dir))`, so label[i] corresponds to the
i-th sorted .mrc filename. We reconstruct that exact order from the input
pickle keys (authoritative) and emit `file,pred_label` CSVs matching the
pytom/opus convention.

Usage (run from repo root):
  conda run -n relion-5.0 python3 scripts/eval/score_disca_t4p.py
"""
import os
import pickle
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import adjusted_rand_score, adjusted_mutual_info_score

REPO = Path(__file__).resolve().parents[2]

INPUT_PICKLE = Path.home() / "Research/disca_work/disca_input_672_cyl_v2.pickle"
LABEL_DIR = Path.home() / "Research/disca_work/model_cyl_v2"
OUT_DIR = REPO / "results"

# Soft-GT references (post-reorg canonical paths)
REFS = [
    dict(name="PEET",  csv=REPO / "packages/peet/T4P/results/peet_final_class_assignments_v2.csv",
         id_col="particle", label_col="class", sep=","),
    dict(name="Dynamo", csv=REPO / "packages/dynamo/T4P/results/dynamo_final_results/class_assignments.csv",
         id_col="particle", label_col="class", sep=","),
    dict(name="PyTom", csv=REPO / "results/pytom_v2mask_k2.csv",
         id_col="file", label_col="pred_label", sep=","),
]


def load_ref(cfg):
    df = pd.read_csv(cfg["csv"], sep=cfg["sep"])
    df[cfg["id_col"]] = df[cfg["id_col"]].apply(lambda x: os.path.basename(str(x)))
    return df.set_index(cfg["id_col"])[cfg["label_col"]]


def main():
    with open(INPUT_PICKLE, "rb") as f:
        data = pickle.load(f)
    # Authoritative order: same comprehension DISCA uses
    keys = [k for k in data["vs"] if data["vs"][k]["v"] is not None]
    print(f"input pickle: {len(keys)} particles")

    refs = {}
    for cfg in REFS:
        if cfg["csv"].exists():
            refs[cfg["name"]] = load_ref(cfg)
        else:
            print(f"WARNING: missing ref {cfg['name']}: {cfg['csv']}")

    for k in (2, 3, 4):
        lbl_path = LABEL_DIR / f"labels_cyl_v2_k{k}.pickle"
        if not lbl_path.exists():
            continue
        with open(lbl_path, "rb") as f:
            labels = np.asarray(pickle.load(f))
        assert len(labels) == len(keys), f"label/key length mismatch k={k}"

        files = [f"{key}.mrc" for key in keys]
        out_csv = OUT_DIR / f"disca_cyl_v2_k{k}.csv"
        pd.DataFrame({"file": files, "pred_label": labels}).to_csv(out_csv, index=False)
        sizes = np.bincount(labels)
        print(f"\nk={k}: sizes={sizes.tolist()}  -> {out_csv.relative_to(REPO)}")

        s_disca = pd.Series(labels, index=files)
        for name, s_ref in refs.items():
            shared = s_disca.index.intersection(s_ref.index)
            if len(shared) == 0:
                print(f"  vs {name}: no shared particles")
                continue
            a = s_disca.loc[shared].values
            b = s_ref.loc[shared].values
            ari = adjusted_rand_score(b, a)
            ami = adjusted_mutual_info_score(b, a)
            print(f"  vs {name:7s} (n={len(shared)}): ARI={ari:+.3f}  AMI={ami:+.3f}")


if __name__ == "__main__":
    main()
