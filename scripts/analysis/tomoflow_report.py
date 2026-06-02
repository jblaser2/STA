#!/usr/bin/env python3
"""
tomoflow_report.py — analyse the TomoFlow conformational landscape on T4P.

Reads the PCA embedding produced by tomoflow_run.py, renders the 2D
conformational landscape (+ PC1 histogram to test for the bimodality expected
from two pili phases), k-means clusters it at k=2/3/4, builds class averages
from the full-resolution 80^3 originals, computes inter-class normalised
cross-correlation, and renders central slices per class.

The headline question: does TomoFlow's continuous landscape resolve the TWO
distinct pili-phase classes that Dynamo finds (i.e. is PC1 visibly bimodal,
and do the k=2 class averages differ)?

Outputs: tomoflow/results/ (RESULTS.md + PNGs). Run in the `tomoflow` env.
"""
import argparse, os
import numpy as np
import mrcfile
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from sklearn.cluster import KMeans
from scipy.stats import gaussian_kde


def class_average(keys, subtomo_dir):
    acc = None
    for key in keys:
        with mrcfile.open(os.path.join(subtomo_dir, key + ".mrc"), permissive=True) as m:
            d = m.data.astype(np.float64)
        acc = d if acc is None else acc + d
    return (acc / len(keys)).astype(np.float32)


def ncc(a, b):
    a = (a - a.mean()) / (a.std() + 1e-8)
    b = (b - b.mean()) / (b.std() + 1e-8)
    return float((a * b).mean())


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--work", default=os.path.expanduser("~/Research/tomoflow_work"))
    ap.add_argument("--subtomo-dir", default="subtomos_mrc")
    ap.add_argument("--out-dir", default="tomoflow/results")
    ap.add_argument("--ks", default="2,3,4")
    args = ap.parse_args()

    os.makedirs(args.out_dir, exist_ok=True)
    emb = np.load(os.path.join(args.work, "embedding.npy"))
    keys = open(os.path.join(args.work, "keys.txt")).read().split()
    assert len(keys) == len(emb), f"{len(keys)} keys vs {len(emb)} embedding rows"
    n = len(emb)

    # --- landscape + PC1 bimodality test ---
    fig, ax = plt.subplots(1, 2, figsize=(10, 4))
    ax[0].scatter(emb[:, 0], emb[:, 1] if emb.shape[1] > 1 else np.zeros(n),
                  s=8, alpha=0.5)
    ax[0].set_xlabel("PC1"); ax[0].set_ylabel("PC2"); ax[0].set_title("TomoFlow conformational landscape")
    xs = np.linspace(emb[:, 0].min(), emb[:, 0].max(), 200)
    ax[1].hist(emb[:, 0], bins=40, density=True, alpha=0.4, color="gray")
    try:
        ax[1].plot(xs, gaussian_kde(emb[:, 0])(xs), "b-")
    except Exception:
        pass
    ax[1].set_xlabel("PC1"); ax[1].set_title("PC1 density (bimodal = two phases?)")
    fig.tight_layout(); fig.savefig(os.path.join(args.out_dir, "tomoflow_landscape.png"), dpi=120)
    plt.close(fig)

    lines = ["# TomoFlow conformational analysis — T4P (672 subtomograms)\n",
             "3D optical flow (farneback3d) vs global average → PCA landscape → k-means.\n",
             "| k | class sizes (occupancy) | inter-class CC |", "|---|---|---|"]

    for ks in args.ks.split(","):
        k = int(ks)
        km = KMeans(n_clusters=k, n_init=10, random_state=0).fit(emb)
        labels = km.labels_
        sizes, avgs = [], []
        for c in range(k):
            ckeys = [keys[i] for i in range(n) if labels[i] == c]
            sizes.append(len(ckeys)); avgs.append(class_average(ckeys, args.subtomo_dir))
        ccs = [ncc(avgs[a], avgs[b]) for a in range(k) for b in range(a + 1, k)]
        cc_str = (f"{min(ccs):.3f}–{max(ccs):.3f}" if len(ccs) > 1 else (f"{ccs[0]:.3f}" if ccs else "n/a"))
        occ = ", ".join(f"{s} ({100*s/n:.0f}%)" for s in sizes)
        lines.append(f"| {k} | {occ} | {cc_str} |")

        # class average slices
        fig, axes = plt.subplots(k, 3, figsize=(7.5, 2.6 * k), squeeze=False)
        for r, av in enumerate(avgs):
            cc = av.shape[0] // 2
            for col, (pl, sl) in enumerate([("XY", av[cc]), ("XZ", av[:, cc]), ("YZ", av[:, :, cc])]):
                a = axes[r][col]; a.imshow(sl, cmap="gray"); a.set_xticks([]); a.set_yticks([])
                if col == 0: a.set_ylabel(f"class {r} (n={sizes[r]})", fontsize=9)
                if r == 0: a.set_title(pl, fontsize=10)
        fig.suptitle(f"TomoFlow k={k} class averages", fontsize=11)
        fig.tight_layout(rect=[0, 0, 1, 0.97])
        fig.savefig(os.path.join(args.out_dir, f"tomoflow_k{k}_classes.png"), dpi=110)
        plt.close(fig)
        print(f"k={k}: sizes={sizes} cc={cc_str}")

    with open(os.path.join(args.out_dir, "RESULTS.md"), "w") as f:
        f.write("\n".join(lines) + "\n")
    print("wrote", os.path.join(args.out_dir, "RESULTS.md"))


if __name__ == "__main__":
    main()
