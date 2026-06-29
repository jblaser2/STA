#!/usr/bin/env python3
"""
noise_perturb_t4p.py — embedding-space noise robustness test for T4P.

For each available embedding (currently: Dynamo UMAP/t-SNE), adds Gaussian
noise N(0, σ × dim_std) to each embedding dimension at several noise levels,
re-runs k-means, and computes ARI between the original assignments and
the noisy re-cluster.  Repeats 10× per noise level and reports mean ± SD ARI.

High ARI under noise → clusters are robust to embedding perturbation →
not fitting embedding-space artifacts.

NOTE: This tests k-means robustness in saved 2D embedding space, not full
pipeline robustness on raw voxel data.  For voxel-space validation, add
Gaussian noise to .mrc subtomograms and re-run PEET (see plan notes).

Usage (run from repo root):
  python3 scripts/eval/noise_perturb_t4p.py
  python3 scripts/eval/noise_perturb_t4p.py --sigmas 0.1 0.25 0.5 1.0 2.0 \
      --repeats 20 --out packages/figures/T4P/noise_perturb.png
"""
import argparse
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from pathlib import Path
from sklearn.cluster import KMeans
from sklearn.metrics import adjusted_rand_score

REPO = Path(__file__).resolve().parents[2]

EMBEDDINGS = [
    dict(
        name="Dynamo",
        csv=REPO / "packages/dynamo/T4P/results/dynamo_final_results/embedding_coords.csv",
        id_col="particle",
        label_col="class",
        coord_cols_sets=[
            ("UMAP", ["umap1", "umap2"]),
            ("t-SNE", ["tsne1", "tsne2"]),
        ],
    ),
]

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


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--sigmas", type=float, nargs="+", default=DEFAULT_SIGMAS,
                    help="Noise levels as multiples of per-dim std")
    ap.add_argument("--repeats", type=int, default=10,
                    help="Repeats per noise level (default 10)")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--out",
                    default="packages/figures/T4P/noise_perturb.png",
                    help="Output figure path")
    args = ap.parse_args()

    sigmas = sorted(args.sigmas)
    results = {}  # (pkg_name, coord_name) -> list of (sigma, mean_ari, std_ari)

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
            key = (emb["name"], coord_name)
            results[key] = []

            print(f"  [{coord_name}]")
            for sigma in sigmas:
                mean_ari, std_ari = noisy_ari(X, orig_labels, sigma, k, args.repeats, args.seed)
                results[key].append((sigma, mean_ari, std_ari))
                print(f"    σ={sigma:.2f}: ARI = {mean_ari:.3f} ± {std_ari:.3f}")
        print()

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
