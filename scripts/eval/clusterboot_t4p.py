#!/usr/bin/env python3
"""
clusterboot_t4p.py — Hennig (2007) bootstrap cluster stability for T4P.

For each package with accessible embedding coordinates, draws 80% particle
subsamples without replacement, re-runs k-means on the subsample, then
measures per-cluster Jaccard similarity between the bootstrap clusters and
the original clusters.  Reports mean ± SD Jaccard per cluster and the
size-weighted average.

Packages with accessible embeddings:
  Dynamo — UMAP + tSNE (embedding_coords.csv, 672 particles)
  PEET   — PCA coefficients (pca672_peet_wedge.mat::coeffs, 672×20)

PyTom and ProTomo lack accessible embedding coordinates and are skipped.

NOTE: this tests stability of k-means re-clustering in saved embedding space,
not full pipeline re-runs.  True Hennig stability would require re-running
each package on each subsample (infeasible for this benchmark).

Usage (run from repo root):
  conda run -n eman2 python3 scripts/eval/clusterboot_t4p.py
  conda run -n eman2 python3 scripts/eval/clusterboot_t4p.py \
      --n-boot 20 --resample 0.8 --seed 42 \
      --out results/T4P/clusterboot_summary.csv
"""
import argparse
import numpy as np
import pandas as pd
import h5py
from pathlib import Path
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler

REPO = Path(__file__).resolve().parents[2]

PEET_MAT = Path("/home/jblaser2/Research/peet/results/pca672_peet_wedge.mat")
PEET_CSV = REPO / "results/T4P/peet_k3_std.csv"


def jaccard(set_a: set, set_b: set) -> float:
    inter = len(set_a & set_b)
    union = len(set_a | set_b)
    return inter / union if union > 0 else 0.0


def clusterboot(X: np.ndarray, labels_orig: np.ndarray,
                n_boot: int, resample_frac: float,
                k: int, seed: int) -> dict:
    """Return per-cluster mean/SD Jaccard and size-weighted average."""
    rng = np.random.default_rng(seed)
    n = len(X)
    classes = sorted(np.unique(labels_orig))
    orig_sets = {c: set(np.where(labels_orig == c)[0]) for c in classes}
    all_jaccards = {c: [] for c in classes}

    for b in range(n_boot):
        idx = rng.choice(n, size=int(n * resample_frac), replace=False)
        km = KMeans(n_clusters=k, n_init=10, random_state=int(rng.integers(0, 2**31)))
        boot_labels = km.fit_predict(X[idx])
        boot_sets = {bc: set(idx[boot_labels == bc]) for bc in np.unique(boot_labels)}
        for c in classes:
            best_j = max(jaccard(orig_sets[c], bs) for bs in boot_sets.values())
            all_jaccards[c].append(best_j)

    result = {}
    weighted_sum, total_weight = 0.0, 0.0
    for c in classes:
        arr = np.array(all_jaccards[c])
        result[c] = {"mean": float(arr.mean()), "std": float(arr.std()),
                     "size": len(orig_sets[c])}
        weighted_sum += arr.mean() * len(orig_sets[c])
        total_weight += len(orig_sets[c])
    result["weighted_avg"] = weighted_sum / total_weight if total_weight > 0 else 0.0
    return result


def load_peet_embedding() -> tuple[np.ndarray, np.ndarray] | None:
    """Load PEET PCA coefficients and class labels; return (X, labels)."""
    if not PEET_MAT.exists() or not PEET_CSV.exists():
        return None
    with h5py.File(PEET_MAT, "r") as f:
        coeffs = f["coeffs"][:].astype(np.float32)  # (672, 20)
    df = pd.read_csv(PEET_CSV)
    # Use top 10 PCA components; StandardScaler before k-means
    X = StandardScaler().fit_transform(coeffs[:, :10])
    # peet_k3_std has class_int 1/2/3; map to 0-indexed for k-means comparison
    labels = df["class_int"].values - 1
    return X, labels


def print_result(pkg_name: str, coord_name: str, result: dict,
                 labels_orig: np.ndarray, rows: list):
    classes = sorted(c for c in result if c != "weighted_avg")
    ws = result["weighted_avg"]
    ws_flag = (
        "STABLE" if ws >= 0.75 else "MODERATE" if ws >= 0.5 else "FRAGILE"
    )
    print(f"  [{coord_name}]  weighted avg Jaccard = {ws:.3f}  [{ws_flag}]")
    for c in classes:
        r = result[c]
        flag = "" if r["mean"] >= 0.75 else " (moderate)" if r["mean"] >= 0.5 else "  *** FRAGILE"
        print(f"    class {c} (n={r['size']}): Jaccard = {r['mean']:.3f} ± {r['std']:.3f}{flag}")
        rows.append(dict(package=pkg_name, embedding=coord_name,
                         cluster=c, n=r["size"],
                         jaccard_mean=r["mean"], jaccard_sd=r["std"],
                         weighted_stability=ws))


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--n-boot", type=int, default=20)
    ap.add_argument("--resample", type=float, default=0.8)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--out", default="results/T4P/clusterboot_summary.csv")
    args = ap.parse_args()

    print(f"Hennig clusterboot: n_boot={args.n_boot}, resample={args.resample:.0%}\n")
    rows = []

    # --- Dynamo (UMAP + tSNE) ---
    dyn_csv = REPO / "packages/dynamo/T4P/results/dynamo_final_results/embedding_coords.csv"
    if dyn_csv.exists():
        df = pd.read_csv(dyn_csv)
        orig_labels = df["class"].values
        k = len(np.unique(orig_labels))
        print(f"=== Dynamo (k={k}, n={len(df)}) ===")
        for coord_name, cols in [("umap", ["umap1", "umap2"]),
                                  ("tsne", ["tsne1", "tsne2"])]:
            if not all(c in df.columns for c in cols):
                continue
            X = StandardScaler().fit_transform(df[cols].values)
            result = clusterboot(X, orig_labels, args.n_boot, args.resample, k, args.seed)
            print_result("Dynamo", coord_name, result, orig_labels, rows)
        print()
    else:
        print("WARNING: Dynamo embedding not found — skipping\n")

    # --- PEET (PCA coefficients) ---
    peet_data = load_peet_embedding()
    if peet_data is not None:
        X_peet, labels_peet = peet_data
        k_peet = len(np.unique(labels_peet))
        print(f"=== PEET (k={k_peet}, n={len(labels_peet)}, top-10 PCA) ===")
        result = clusterboot(X_peet, labels_peet, args.n_boot, args.resample, k_peet, args.seed)
        print_result("PEET", "pca", result, labels_peet, rows)
        print()
    else:
        print("WARNING: PEET embedding (.mat or std CSV) not found — skipping\n")

    if rows:
        out = REPO / args.out
        out.parent.mkdir(parents=True, exist_ok=True)
        pd.DataFrame(rows).to_csv(out, index=False)
        print(f"Saved: {out}")

    print("\nStability thresholds (Hennig 2007 adapted):")
    print("  Jaccard >= 0.75 : stable — publishable claim")
    print("  Jaccard 0.5-0.75: moderately stable — note in paper")
    print("  Jaccard <  0.50 : fragile — flag as caveated result")
    print()
    print("Note: PyTom and ProTomo lack saved embedding coordinates;")
    print("  use cross-package consensus score as stability proxy.")


if __name__ == "__main__":
    main()
