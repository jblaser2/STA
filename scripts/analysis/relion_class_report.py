#!/usr/bin/env python3
"""
relion_class_report.py — summarize the RELION Class3D matrix on the T4P subtomograms.

For each run dir outputs/relion/Class3D/k{K}_{ctf}/ it:
  - parses the final run_it{ITER}_model.star  -> per-class distribution + resolution
  - parses the final run_it{ITER}_data.star   -> per-particle class assignment counts
  - loads run_it{ITER}_class00N.mrc            -> inter-class cross-correlation
  - renders central XY/XZ/YZ slices per class  -> one PNG per run
Outputs a markdown summary table + per-run slice figures under outputs/relion/results/.

Run in an env with numpy + mrcfile + matplotlib (e.g. relion-5.0).
"""
import argparse
import glob
import os
import numpy as np
import mrcfile
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


def parse_star_loop(path, block):
    """Return (columns:list[str], rows:list[list[str]]) for a named data_ block."""
    cols, rows = [], []
    with open(path) as f:
        lines = f.read().splitlines()
    i = 0
    # find block
    while i < len(lines) and lines[i].strip() != block:
        i += 1
    # find loop_
    while i < len(lines) and lines[i].strip() != "loop_":
        i += 1
    i += 1
    # column headers
    while i < len(lines) and lines[i].strip().startswith("_"):
        cols.append(lines[i].strip().split()[0])
        i += 1
    # data rows until blank or next data_
    while i < len(lines):
        s = lines[i].strip()
        if not s or s.startswith("data_") or s == "loop_":
            break
        rows.append(s.split())
        i += 1
    return cols, rows


def col_idx(cols, name):
    return cols.index(name)


def ncc(a, b):
    a = (a - a.mean()).ravel()
    b = (b - b.mean()).ravel()
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-12))


def central_slices(vol):
    c = vol.shape[0] // 2
    return vol[c, :, :], vol[:, c, :], vol[:, :, c]  # XY, XZ, YZ


def process_run(run_dir, iter_n):
    model = os.path.join(run_dir, f"run_it{iter_n:03d}_model.star")
    data = os.path.join(run_dir, f"run_it{iter_n:03d}_data.star")
    if not os.path.exists(model):
        # fall back to whatever last model exists
        ms = sorted(glob.glob(os.path.join(run_dir, "run_it*_model.star")))
        if not ms:
            return None
        model = ms[-1]
        iter_n = int(os.path.basename(model).split("_it")[1][:3])
        data = os.path.join(run_dir, f"run_it{iter_n:03d}_data.star")

    cols, rows = parse_star_loop(model, "data_model_classes")
    ref_i = col_idx(cols, "_rlnReferenceImage")
    dist_i = col_idx(cols, "_rlnClassDistribution")
    res_i = col_idx(cols, "_rlnEstimatedResolution") if "_rlnEstimatedResolution" in cols else None
    classes = []
    for r in rows:
        classes.append({
            "ref": r[ref_i],
            "dist": float(r[dist_i]),
            "res": float(r[res_i]) if res_i is not None else None,
        })

    # per-particle counts from data.star
    dcols, drows = parse_star_loop(data, "data_particles")
    counts = {}
    if "_rlnClassNumber" in dcols:
        cn = col_idx(dcols, "_rlnClassNumber")
        for r in drows:
            k = int(r[cn])
            counts[k] = counts.get(k, 0) + 1

    # load maps
    vols = []
    for c in classes:
        mp = c["ref"]
        if not os.path.isabs(mp) and not os.path.exists(mp):
            mp = os.path.join(run_dir, os.path.basename(mp))
        with mrcfile.open(mp, permissive=True) as m:
            vols.append(np.array(m.data, dtype=np.float32))

    # pairwise CC
    ccs = []
    for a in range(len(vols)):
        for b in range(a + 1, len(vols)):
            ccs.append(((a + 1, b + 1), ncc(vols[a], vols[b])))

    return {"iter": iter_n, "classes": classes, "counts": counts,
            "vols": vols, "ccs": ccs}


def render_figure(run_name, info, out_png):
    vols = info["vols"]
    K = len(vols)
    fig, axes = plt.subplots(K, 3, figsize=(7.5, 2.6 * K), squeeze=False)
    views = ["XY", "XZ", "YZ"]
    for k, vol in enumerate(vols):
        sls = central_slices(vol)
        dist = info["classes"][k]["dist"]
        cnt = info["counts"].get(k + 1, 0)
        for j, sl in enumerate(sls):
            ax = axes[k][j]
            ax.imshow(sl, cmap="gray")
            ax.set_xticks([]); ax.set_yticks([])
            if k == 0:
                ax.set_title(views[j], fontsize=10)
            if j == 0:
                ax.set_ylabel(f"class {k+1}\n{cnt} ptcl ({dist*100:.0f}%)", fontsize=9)
    fig.suptitle(run_name, fontsize=12)
    fig.tight_layout(rect=[0, 0, 1, 0.97])
    fig.savefig(out_png, dpi=130)
    plt.close(fig)


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root", default="outputs/relion/Class3D")
    ap.add_argument("--out", default="outputs/relion/results")
    ap.add_argument("--iter", type=int, default=25)
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)

    run_dirs = sorted(glob.glob(os.path.join(args.root, "k*_*")))
    table = ["| Run | k | CTF | Class sizes (occupancy) | Inter-class CC | Resolution (Å) |",
             "|---|---|---|---|---|---|"]
    for rd in run_dirs:
        name = os.path.basename(rd)
        info = process_run(rd, args.iter)
        if info is None:
            print(f"skip {name}: no model.star")
            continue
        k = name.split("_")[0][1:]
        ctf = name.split("_")[1]
        sizes = ", ".join(
            f"{info['counts'].get(i+1,0)} ({c['dist']*100:.0f}%)"
            for i, c in enumerate(info["classes"]))
        cc = ", ".join(f"{p[0]}v{p[1]}={v:.3f}" for p, v in info["ccs"])
        res = ", ".join(f"{c['res']:.1f}" if c["res"] else "-" for c in info["classes"])
        table.append(f"| {name} | {k} | {ctf} | {sizes} | {cc} | {res} |")
        png = os.path.join(args.out, f"{name}_slices.png")
        render_figure(name, info, png)
        print(f"{name}: sizes=[{sizes}]  CC=[{cc}]")

    md = os.path.join(args.out, "RESULTS.md")
    with open(md, "w") as f:
        f.write("# RELION 3D-subtomogram classification — T4P results\n\n")
        f.write("\n".join(table) + "\n")
    print(f"\nwrote {md} and per-run slice PNGs to {args.out}/")


if __name__ == "__main__":
    main()
