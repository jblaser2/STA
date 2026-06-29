#!/usr/bin/env python3
"""
clusterboot_t4p.py — Hennig (2007) bootstrap cluster stability for T4P.

For each available embedding (currently: Dynamo UMAP/t-SNE), draws 80%
particle subsamples without replacement, re-runs k-means on the subsample,
then measures per-cluster Jaccard similarity between the bootstrap clusters
and the original clusters.  Reports mean ± SD Jaccard per cluster and the
size-weighted average.

Cross-package consensus (already computed in build_labels_matrix.py) is the
complementary stability measure for packages without saved embeddings (PEET,
PyTom, ProTomo).

NOTE: this tests stability of k-means re-clustering in saved embedding space,
not full pipeline re-runs.  True Hennig stability would require re-running
each package on each subsample (infeasible for this benchmark).

Usage (run from repo root):
  python3 scripts/eval/clusterboot_t4p.py
  python3 scripts/eval/clusterboot_t4p.py --n-boot 20 --resample 0.8 --seed 42
"""
import argparse
import numpy as np
import pandas as pd
from pathlib import Path
from sklearn.cluster import KMeans

REPO = Path(__file__).resolve().parents[2]

EMBEDDINGS = [
    dict(
        name="Dynamo",
        csv=REPO / "packages/dynamo/T4P/results/dynamo_final_results/embedding_coords.csv",
        id_col="particle",
        label_col="class",
        coord_cols_sets=[
            ("umap", ["umap1", "umap2"]),
            ("tsne", ["tsne1", "tsne2"]),
        ],
    ),
]


def jaccard(set_a: set, set_b: set) -> float:
    inter = len(set_a & set_b)
    union = len(set_a | set_b)
    return inter / union if union > 0 else 0.0


def clusterboot(X: np.ndarray, labels_orig: np.ndarray,
                n_boot: int, resample_frac: float,
                k: int, seed: int) -> dict:
    """
    Run Hennig clusterboot.

    Returns dict with per-cluster mean/std Jaccard and size-weighted average.
    """
    rng = np.random.default_rng(seed)
    n = len(X)
    classes = sorted(np.unique(labels_orig))

    # Original clusters as index sets
    orig_sets = {c: set(np.where(labels_orig == c)[0]) for c in classes}

    all_jaccards = {c: [] for c in classes}

    for _ in range(n_boot):
        idx = rng.choice(n, size=int(n * resample_frac), replace=False)
        X_sub = X[idx]

        km = KMeans(n_clusters=k, n_init=10, random_state=rng.integers(0, 2**31))
        boot_labels = km.fit_predict(X_sub)

        boot_classes = sorted(np.unique(boot_labels))
        # boot cluster index sets (in terms of *original* particle indices)
        boot_sets = {bc: set(idx[boot_labels == bc]) for bc in boot_classes}

        # For each original cluster, find best-matching bootstrap cluster
        for c in classes:
            best_j = max(
                jaccard(orig_sets[c], bs) for bs in boot_sets.values()
            )
            all_jaccards[c].append(best_j)

    result = {}
    total_weight = 0.0
    weighted_sum = 0.0
    for c in classes:
        arr = np.array(all_jaccards[c])
        result[c] = {"mean": float(arr.mean()), "std": float(arr.std())}
        w = len(orig_sets[c])
        weighted_sum += arr.mean() * w
        total_weight += w

    result["weighted_avg"] = weighted_sum / total_weight if total_weight > 0 else 0.0
    return result


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--n-boot", type=int, default=20, help="Bootstrap draws (default 20)")
    ap.add_argument("--resample", type=float, default=0.8,
                    help="Resample fraction 0-1 (default 0.8)")
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()

    print(f"Hennig clusterboot: n_boot={args.n_boot}, resample={args.resample:.0%}\n")

    for emb in EMBEDDINGS:
        csv = emb["csv"]
        if not csv.exists():
            print(f"WARNING: {emb['name']} embedding not found: {csv}")
            continue

        df = pd.read_csv(csv)
        orig_labels = df[emb["label_col"]].values
        k = len(np.unique(orig_labels))

        print(f"=== {emb['name']} (k={k}, n={len(df)}) ===")

        for coord_name, cols in emb["coord_cols_sets"]:
            missing_cols = [c for c in cols if c not in df.columns]
            if missing_cols:
                print(f"  [{coord_name}] missing columns: {missing_cols} — skipping")
                continue

            X = df[cols].values
            result = clusterboot(X, orig_labels, args.n_boot, args.resample, k, args.seed)

            print(f"  [{coord_name}]  weighted avg Jaccard = {result['weighted_avg']:.3f}")
            classes = sorted(c for c in result if c != "weighted_avg")
            for c in classes:
                r = result[c]
                n_cls = int((orig_labels == c).sum())
                flag = ""
                if r["mean"] < 0.5:
                    flag = "  *** FRAGILE"
                elif r["mean"] < 0.75:
                    flag = "  (moderate)"
                print(f"    class {c} (n={n_cls}): Jaccard = {r['mean']:.3f} ± {r['std']:.3f}{flag}")
        print()

    print("Stability thresholds (Hennig 2007 adapted):")
    print("  Jaccard >= 0.75 : stable — publishable claim")
    print("  Jaccard 0.5-0.75: moderately stable — note in paper")
    print("  Jaccard <  0.50 : fragile — caveat result")
    print()
    print("Note: only Dynamo has saved embedding coordinates.")
    print("For PEET/PyTom/ProTomo stability, see cross-package consensus in")
    print("  outputs/benchmark/T4P_labels_matrix.csv (357/672 = 53% high-consensus).")


if __name__ == "__main__":
    main()
