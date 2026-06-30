#!/usr/bin/env python3
"""
noise_perturb_t4p.py — embedding-space noise robustness test for T4P.

For each package with accessible embedding coordinates, adds Gaussian noise
N(0, σ × dim_std) to each embedding dimension at several noise levels,
re-runs k-means, and computes ARI between the original assignments and the
noisy re-cluster.  Repeats 10× per noise level and reports mean ± SD ARI.

High ARI under noise → clusters are robust to embedding perturbation →
not fitting embedding-space artifacts.

Packages tested:
  Dynamo — UMAP + tSNE (embedding_coords.csv)
  PEET   — PCA coefficients (pca672_peet_wedge.mat, top-10 components)

PyTom and ProTomo lack accessible embedding coordinates and are skipped.

NOTE: This tests k-means robustness in saved embedding space, not full
pipeline robustness on raw voxel data.  For voxel-space validation, add
Gaussian noise to .mrc subtomograms and re-run PEET (deferred).

Usage (run from repo root):
  conda run -n eman2 python3 scripts/eval/noise_perturb_t4p.py
  conda run -n eman2 python3 scripts/eval/noise_perturb_t4p.py \
      --sigmas 0.1 0.25 0.5 1.0 2.0 --repeats 20 \
      --out packages/figures/T4P/noise_perturb.png
"""
import argparse
import numpy as np
import pandas as pd
import h5py
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from pathlib import Path
from sklearn.cluster import KMeans
from sklearn.metrics import adjusted_rand_score
from sklearn.preprocessing import StandardScaler

REPO = Path(__file__).resolve().parents[2]
PEET_MAT = Path("/home/jblaser2/Research/peet/results/pca672_peet_wedge.mat")
PEET_CSV = REPO / "results/T4P/peet_k3_std.csv"

DEFAULT_SIGMAS = [0.0, 0.1, 0.25, 0.5, 1.0, 1.5, 2.0]


def noisy_ari(X: np.ndarray, orig_labels: np.ndarray,
              sigma: float, k: int, repeats: int, seed: int) -> tuple[float, float]:
    """Return (mean_ARI, std_ARI) over `repeats` noise draws."""
    rng = np.random.default_rng(seed)
    dim_std = X.std(axis=0)
    aris = []
    for _ in range(repeats):
        noise = rng.standard_normal(X.shape) * sigma * dim_std
        X_noisy = X + noise
        km = KMeans(n_clusters=k, n_init=10, random_state=rng.integers(0, 2**31))
        labels_noisy = km.fit_predict(X_noisy)
        aris.append(adjusted_rand_score(orig_labels, labels_noisy))
    return float(np.mean(aris)), float(np.std(aris))


def run_pkg(name: str, coord_name: str, X: np.ndarray, orig_labels: np.ndarray,
            sigmas: list, repeats: int, seed: int) -> list:
    k = len(np.unique(orig_labels))
    print(f"  [{coord_name}]")
    rows = []
    for sigma in sigmas:
        mean_ari, std_ari = noisy_ari(X, orig_labels, sigma, k, repeats, seed)
        print(f"    σ={sigma:.2f}: ARI = {mean_ari:.3f} ± {std_ari:.3f}")
        rows.append((sigma, mean_ari, std_ari))
    return rows


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--sigmas", type=float, nargs="+", default=DEFAULT_SIGMAS,
                    help="Noise levels as multiples of per-dim std")
    ap.add_argument("--repeats", type=int, default=10)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--out", default="packages/figures/T4P/noise_perturb.png")
    ap.add_argument("--csv-out", default="results/T4P/noise_perturb_summary.csv")
    args = ap.parse_args()

    sigmas = sorted(args.sigmas)
    results = {}  # (pkg_name, coord_name) -> list of (sigma, mean_ari, std_ari)

    # --- Dynamo ---
    dyn_csv = REPO / "packages/dynamo/T4P/results/dynamo_final_results/embedding_coords.csv"
    if dyn_csv.exists():
        df = pd.read_csv(dyn_csv)
        orig = df["class"].values
        print(f"=== Dynamo (k={len(np.unique(orig))}, n={len(df)}) ===")
        for coord_name, cols in [("UMAP", ["umap1", "umap2"]),
                                  ("t-SNE", ["tsne1", "tsne2"])]:
            if not all(c in df.columns for c in cols):
                continue
            X = StandardScaler().fit_transform(df[cols].values)
            results[("Dynamo", coord_name)] = run_pkg("Dynamo", coord_name, X, orig,
                                                       sigmas, args.repeats, args.seed)
        print()
    else:
        print("WARNING: Dynamo embedding not found — skipping\n")

    # --- PEET ---
    if PEET_MAT.exists() and PEET_CSV.exists():
        with h5py.File(PEET_MAT, "r") as f:
            coeffs = f["coeffs"][:, :10].astype(np.float32)
        peet_df = pd.read_csv(PEET_CSV)
        orig = peet_df["class_int"].values - 1  # 0-indexed
        X_peet = StandardScaler().fit_transform(coeffs)
        print(f"=== PEET (k={len(np.unique(orig))}, n={len(orig)}, top-10 PCA) ===")
        results[("PEET", "PCA")] = run_pkg("PEET", "PCA", X_peet, orig,
                                            sigmas, args.repeats, args.seed)
        print()
    else:
        print("WARNING: PEET embedding (.mat or std CSV) not found — skipping\n")

    # Save CSV
    if results:
        csv_rows = []
        for (pkg, coord), pkg_rows in results.items():
            for sigma, mean_ari, std_ari in pkg_rows:
                csv_rows.append(dict(package=pkg, embedding=coord,
                                     sigma=sigma, ari_mean=mean_ari, ari_sd=std_ari))
        csv_out = REPO / args.csv_out
        csv_out.parent.mkdir(parents=True, exist_ok=True)
        pd.DataFrame(csv_rows).to_csv(csv_out, index=False)
        print(f"Saved CSV: {csv_out}")

    # Plot
    if not results:
        print("No results to plot.")
        return

    fig, ax = plt.subplots(figsize=(6, 4))
    colors = plt.cm.tab10.colors
    for (pkg, coord), rows in results.items():
        sigs = [r[0] for r in rows]
        means = [r[1] for r in rows]
        stds = [r[2] for r in rows]
        label = f"{pkg} [{coord}]"
        c = colors[list(results).index((pkg, coord)) % len(colors)]
        ax.plot(sigs, means, marker="o", label=label, color=c)
        ax.fill_between(sigs,
                        [m - s for m, s in zip(means, stds)],
                        [m + s for m, s in zip(means, stds)],
                        alpha=0.2, color=c)

    ax.axhline(0.7, color="gray", linestyle="--", linewidth=0.8, label="ARI=0.7 (robust threshold)")
    ax.axhline(0.5, color="gray", linestyle=":", linewidth=0.8, label="ARI=0.5")
    ax.set_xlabel("Noise level σ (× per-dim embedding std)", fontsize=10)
    ax.set_ylabel("ARI vs original assignments", fontsize=10)
    ax.set_title("T4P — Embedding-space noise robustness\n(k-means re-cluster after Gaussian perturbation)",
                 fontsize=10)
    ax.set_ylim(-0.05, 1.05)
    ax.legend(fontsize=8)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    plt.tight_layout()
    plt.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved: {out}")

    print("\nInterpretation:")
    print("  ARI > 0.7 at σ=0.5 → clusters robust to moderate embedding noise")
    print("  ARI drops to ~0 at σ=2.0 → expected (pure noise collapses structure)")
    print("  Compare with random-cluster baseline: E[ARI] ≈ 0 for independent k-means runs")


if __name__ == "__main__":
    main()
