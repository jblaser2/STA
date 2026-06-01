#!/usr/bin/env python3
"""
disca_report.py — summarise DISCA clustering of the 672 T4P subtomograms.

For each k-run it reads the saved label pickle (cluster label per particle, in
the same order as DISCA iterated the input container), recovers the per-cluster
particle sets, builds class averages from the FULL-resolution 80^3 originals
(DISCA itself worked on 32^3 downsampled copies), computes inter-class
normalised cross-correlation, and renders central XY/XZ/YZ slices per class.

Outputs: outputs/disca/results/RESULTS.md + PNG figures (small, committable).

Mirrors scripts/analysis/relion_class_report.py so DISCA slots into the same
benchmark comparison (RELION/PyTom/Protomo).

Run in the `disca` env (numpy, scipy, mrcfile, matplotlib).
"""
import argparse
import os
import pickle
import numpy as np
import mrcfile
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


def load_labels(path):
    with open(path, "rb") as f:
        return np.asarray(pickle.load(f))


def particle_keys(input_pickle):
    """Reproduce DISCA's x_keys order: insertion order, v not None."""
    with open(input_pickle, "rb") as f:
        data = pickle.load(f)
    return [k for k in data["vs"] if data["vs"][k]["v"] is not None]


def class_average(keys, subtomo_dir):
    acc = None
    for key in keys:
        p = os.path.join(subtomo_dir, key + ".mrc")
        with mrcfile.open(p, permissive=True) as m:
            d = m.data.astype(np.float64)
        acc = d if acc is None else acc + d
    avg = (acc / len(keys)).astype(np.float32)
    return avg


def ncc(a, b):
    a = (a - a.mean()) / (a.std() + 1e-8)
    b = (b - b.mean()) / (b.std() + 1e-8)
    return float((a * b).mean())


def save_slices(avgs, sizes, k, outpng):
    n = len(avgs)
    fig, axes = plt.subplots(n, 3, figsize=(7.5, 2.6 * n), squeeze=False)
    for r, av in enumerate(avgs):
        c = av.shape[0] // 2
        for col, (plane, sl) in enumerate(
            [("XY", av[c]), ("XZ", av[:, c]), ("YZ", av[:, :, c])]
        ):
            ax = axes[r][col]
            ax.imshow(sl, cmap="gray")
            ax.set_xticks([]); ax.set_yticks([])
            if col == 0:
                ax.set_ylabel(f"class {r}  (n={sizes[r]})", fontsize=9)
            if r == 0:
                ax.set_title(plane, fontsize=10)
    fig.suptitle(f"DISCA k={k} — class averages (central slices)", fontsize=11)
    fig.tight_layout(rect=[0, 0, 1, 0.97])
    fig.savefig(outpng, dpi=110)
    plt.close(fig)


def save_sidebyside(runs, outpng, plane="XY"):
    """One compact comparison figure: rows = k-runs, columns = classes,
    showing each class average's central slice side by side."""
    maxc = max(len(r["avgs"]) for r in runs)
    nrows = len(runs)
    fig, axes = plt.subplots(nrows, maxc, figsize=(2.3 * maxc, 2.5 * nrows),
                             squeeze=False)
    for r, run in enumerate(runs):
        for cidx in range(maxc):
            ax = axes[r][cidx]
            ax.set_xticks([]); ax.set_yticks([])
            if cidx < len(run["avgs"]):
                av = run["avgs"][cidx]
                c = av.shape[0] // 2
                sl = {"XY": av[c], "XZ": av[:, c], "YZ": av[:, :, c]}[plane]
                ax.imshow(sl, cmap="gray")
                ax.set_title(f"n={run['sizes'][cidx]} "
                             f"({100*run['sizes'][cidx]/run['n']:.0f}%)", fontsize=9)
            else:
                ax.axis("off")
            if cidx == 0:
                ax.set_ylabel(f"k={run['k']}", fontsize=11, rotation=0,
                              ha="right", va="center", labelpad=18)
    fig.suptitle(f"DISCA T4P class averages — central {plane} slice "
                 f"(dominant class = crisp pilus; small classes = small-N noise)",
                 fontsize=11)
    fig.tight_layout(rect=[0, 0, 1, 0.96])
    fig.savefig(outpng, dpi=120)
    plt.close(fig)
    print("wrote", outpng)


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--model-dir", default=os.path.expanduser("~/Research/disca_work/model"))
    ap.add_argument("--input-pickle", default=os.path.expanduser("~/Research/disca_work/disca_input_672.pickle"))
    ap.add_argument("--subtomo-dir", default="subtomos_mrc")
    ap.add_argument("--out-dir", default="outputs/disca/results")
    ap.add_argument("--ks", default="2,3,4")
    args = ap.parse_args()

    os.makedirs(args.out_dir, exist_ok=True)
    keys = particle_keys(args.input_pickle)
    runs = []
    lines = ["# DISCA clustering — T4P (672 subtomograms)\n",
             "Unsupervised deep iterative clustering (torch_disca). Averages built from "
             "full-resolution 80^3 originals; DISCA clustered 32^3 downsampled copies.\n",
             "| k | class sizes (occupancy) | inter-class CC |", "|---|---|---|"]

    for ks in args.ks.split(","):
        k = int(ks)
        lab_path = os.path.join(args.model_dir, f"labels_k{k}.pickle")
        if not os.path.exists(lab_path):
            print(f"skip k={k}: no {lab_path}")
            continue
        labels = load_labels(lab_path)
        if len(labels) != len(keys):
            print(f"WARN k={k}: {len(labels)} labels vs {len(keys)} keys")
        uniq = sorted(set(labels.tolist()))
        sizes, avgs = [], []
        for c in uniq:
            ckeys = [keys[i] for i in range(len(labels)) if labels[i] == c]
            sizes.append(len(ckeys))
            avgs.append(class_average(ckeys, args.subtomo_dir))
        # inter-class CC (min..max over distinct pairs)
        ccs = [ncc(avgs[a], avgs[b]) for a in range(len(avgs)) for b in range(a + 1, len(avgs))]
        cc_str = (f"{min(ccs):.3f}–{max(ccs):.3f}" if len(ccs) > 1 else
                  (f"{ccs[0]:.3f}" if ccs else "n/a"))
        occ = ", ".join(f"{s} ({100*s/len(labels):.0f}%)" for s in sizes)
        lines.append(f"| {k} | {occ} | {cc_str} |")
        png = os.path.join(args.out_dir, f"disca_k{k}_classes.png")
        save_slices(avgs, sizes, k, png)
        runs.append({"k": k, "sizes": sizes, "avgs": avgs, "n": len(labels)})
        print(f"k={k}: sizes={sizes} cc={cc_str} -> {png}")

    if runs:
        save_sidebyside(runs, os.path.join(args.out_dir, "disca_class_averages_sidebyside.png"))

    with open(os.path.join(args.out_dir, "RESULTS.md"), "w") as f:
        f.write("\n".join(lines) + "\n")
    print("wrote", os.path.join(args.out_dir, "RESULTS.md"))


if __name__ == "__main__":
    main()
