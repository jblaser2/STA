#!/usr/bin/env python3
"""
gen_t4p_class_avg_panels.py — Standardized class-average figure panels for T4P packages.

For each package: one figure with N panels (ring_complete | ring_altered | junk),
XY central slice only, particle count labeled, saved to packages/figures/T4P/.

For packages without a pre-computed junk-class average MRC (PEET, PyTom, DISCA, OPUS),
class averages are computed on-the-fly from the raw particles using the standardized CSV.

Usage:
  conda run -n eman2 python3 scripts/eval/gen_t4p_class_avg_panels.py
  conda run -n eman2 python3 scripts/eval/gen_t4p_class_avg_panels.py --pkg dynamo
"""

import argparse
import mrcfile
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
from pathlib import Path
from typing import Optional

REPO = Path(__file__).resolve().parents[2]
PARTICLE_DIR = REPO / "data" / "T4P_subtomos"
STD_DIR = REPO / "results" / "T4P"
FIG_DIR = REPO / "packages" / "figures" / "T4P"
FIG_DIR.mkdir(parents=True, exist_ok=True)

# T4P pixel size in Å/px
PIXEL_SIZE = 13.33


def load_mrc(path: Path) -> np.ndarray:
    with mrcfile.open(str(path), permissive=True) as mrc:
        return mrc.data.copy().astype(np.float32)


def compute_class_avg_from_particles(csv_path: Path, class_int: int) -> tuple:
    """Average raw particles for a given class_int. Returns (volume, n_particles)."""
    df = pd.read_csv(csv_path)
    rows = df[df["class_int"] == class_int]
    if rows.empty:
        return None, 0
    acc = None
    count = 0
    for fname in rows["particle"]:
        p = PARTICLE_DIR / fname
        if not p.exists():
            print(f"  WARNING: missing {p.name}")
            continue
        vol = load_mrc(p)
        acc = vol if acc is None else acc + vol
        count += 1
    if acc is None or count == 0:
        return None, 0
    return acc / count, count


def get_class_vol(cls_cfg: dict, csv_path: Optional[Path] = None) -> tuple:
    """Return (volume, n_particles) for one class panel config."""
    if "mrc" in cls_cfg:
        p = cls_cfg["mrc"]
        if not p.exists():
            print(f"  WARNING: MRC not found: {p}")
            return None, cls_cfg.get("n", 0)
        return load_mrc(p), cls_cfg["n"]
    elif "from_particles" in cls_cfg:
        src = cls_cfg["from_particles"]
        print(f"  Computing avg for class_int={cls_cfg['class_int']} from particles...")
        vol, n = compute_class_avg_from_particles(src, cls_cfg["class_int"])
        return vol, n
    return None, 0


def xy_slice(vol: np.ndarray) -> np.ndarray:
    """Central XY slice: data[z, y, x] → data[z_mid, :, :]."""
    z = vol.shape[0] // 2
    return vol[z, :, :]


def normalize_for_display(sl: np.ndarray) -> np.ndarray:
    lo, hi = np.percentile(sl, [2, 98])
    sl = np.clip(sl, lo, hi)
    return (sl - lo) / (hi - lo + 1e-8)


PACKAGES = [
    {
        "name": "Dynamo",
        "key": "dynamo",
        "k": 2,
        "converged": True,
        "classes": [
            {"class_int": 1, "label": "ring_complete", "n": 447,
             "mrc": REPO / "packages/dynamo/T4P/results/dynamo_final_results/class_averages/class_01.mrc"},
            {"class_int": 2, "label": "ring_altered", "n": 225,
             "mrc": REPO / "packages/dynamo/T4P/results/dynamo_final_results/class_averages/class_02.mrc"},
        ],
    },
    {
        "name": "PEET",
        "key": "peet",
        "k": 3,
        "converged": True,
        "classes": [
            {"class_int": 1, "label": "ring_complete", "n": 374,
             "mrc": Path("~/Research/peet/results/final_class_1_avg.mrc").expanduser()},
            {"class_int": 2, "label": "ring_altered", "n": 230,
             "mrc": Path("~/Research/peet/results/final_class_2_avg.mrc").expanduser()},
            {"class_int": 3, "label": "junk", "n": 68,
             "from_particles": STD_DIR / "peet_k3_std.csv"},
        ],
    },
    {
        "name": "PyTom",
        "key": "pytom",
        "k": 3,
        "converged": True,
        "classes": [
            {"class_int": 1, "label": "ring_complete", "n": 422,
             "from_particles": STD_DIR / "pytom_k3_std.csv"},
            {"class_int": 2, "label": "ring_altered", "n": 150,
             "from_particles": STD_DIR / "pytom_k3_std.csv"},
            {"class_int": 3, "label": "junk", "n": 100,
             "from_particles": STD_DIR / "pytom_k3_std.csv"},
        ],
    },
    {
        "name": "ProTomo",
        "key": "protomo",
        "k": 3,
        "converged": True,
        "classes": [
            {"class_int": 1, "label": "ring_complete", "n": 334,
             "mrc": Path("~/Research/protomo/process/results/class_0_avg.mrc").expanduser()},
            {"class_int": 2, "label": "ring_altered", "n": 212,
             "mrc": Path("~/Research/protomo/process/results/class_1_avg.mrc").expanduser()},
            {"class_int": 3, "label": "junk", "n": 126,
             "mrc": Path("~/Research/protomo/process/results/class_2_avg.mrc").expanduser()},
        ],
    },
    {
        "name": "EMAN2",
        "key": "eman2",
        "k": 3,
        "converged": False,
        "classes": [
            # Raw cls02 = 317p → class_int 1 (largest); raw cls01 = 270p → class_int 2
            {"class_int": 1, "label": "class_a", "n": 317,
             "mrc": Path("~/Research/eman2_project/simple_avgs/simple_avg_cls02.mrc").expanduser()},
            {"class_int": 2, "label": "class_b", "n": 270,
             "mrc": Path("~/Research/eman2_project/simple_avgs/simple_avg_cls01.mrc").expanduser()},
            {"class_int": 3, "label": "junk", "n": 85,
             "mrc": Path("~/Research/eman2_project/simple_avgs/simple_avg_cls03.mrc").expanduser()},
        ],
    },
    {
        "name": "DISCA",
        "key": "disca",
        "k": 2,
        "converged": False,
        "note": "k=3 pending",
        "classes": [
            {"class_int": 1, "label": "class_a", "n": 398,
             "from_particles": STD_DIR / "disca_k2_std.csv"},
            {"class_int": 2, "label": "class_b", "n": 274,
             "from_particles": STD_DIR / "disca_k2_std.csv"},
        ],
    },
    {
        "name": "OPUS-TOMO",
        "key": "opus",
        "k": 2,
        "converged": False,
        "note": "k=3 pending",
        "classes": [
            {"class_int": 1, "label": "class_a", "n": 447,
             "from_particles": STD_DIR / "opus_k2_std.csv"},
            {"class_int": 2, "label": "class_b", "n": 225,
             "from_particles": STD_DIR / "opus_k2_std.csv"},
        ],
    },
    {
        "name": "TomoFlow",
        "key": "tomoflow",
        "k": 2,
        "converged": False,
        "note": "masked; ARI≈0 vs Dynamo — noise axis",
        "classes": [
            {"class_int": 0, "label": "class_0", "n": 403,
             "mrc": REPO / "outputs/T4P/tomoflow/tomoflow_k2_class0_avg.mrc"},
            {"class_int": 1, "label": "class_1", "n": 269,
             "mrc": REPO / "outputs/T4P/tomoflow/tomoflow_k2_class1_avg.mrc"},
        ],
    },
]


def make_panel(pkg: dict) -> Path:
    name = pkg["name"]
    key = pkg["key"]
    classes = pkg["classes"]
    k = pkg["k"]
    converged = pkg.get("converged", False)
    note = pkg.get("note", "")
    n_cls = len(classes)

    print(f"\n{'='*50}")
    print(f"  {name}  (k={k}{'  [converged]' if converged else '  [non-converging]'})")

    vols = []
    labels = []
    ns = []
    for cls_cfg in classes:
        vol, n = get_class_vol(cls_cfg)
        vols.append(vol)
        labels.append(cls_cfg["label"])
        ns.append(n)
        status = f"{n}p" if vol is not None else "MISSING"
        print(f"    class_int={cls_cfg['class_int']}  {cls_cfg['label']:15s}  {status}")

    # Build figure
    fig, axes = plt.subplots(1, n_cls, figsize=(3.5 * n_cls, 3.8))
    if n_cls == 1:
        axes = [axes]

    for ax, vol, lbl, n in zip(axes, vols, labels, ns):
        if vol is not None:
            sl = xy_slice(vol)
            sl_norm = normalize_for_display(sl)
            ax.imshow(sl_norm, cmap="gray", origin="lower", vmin=0, vmax=1,
                      interpolation="nearest")
        else:
            ax.set_facecolor("0.15")
            ax.text(0.5, 0.5, "missing", color="white", ha="center", va="center",
                    transform=ax.transAxes, fontsize=11)

        # Class label (top) and particle count (bottom)
        color = "gold" if lbl == "junk" else ("limegreen" if converged else "lightskyblue")
        ax.set_title(f"{lbl}", fontsize=11, color=color, pad=3)
        ax.text(0.97, 0.03, f"n={n}", transform=ax.transAxes,
                ha="right", va="bottom", fontsize=9, color="white",
                bbox=dict(boxstyle="round,pad=0.2", fc="black", alpha=0.6))
        ax.axis("off")

    conv_str = "converged" if converged else "non-converging"
    sup = f"{name}  |  k={k}  |  XY central slice  |  {conv_str}"
    if note:
        sup += f"  [{note}]"
    fig.suptitle(sup, fontsize=12, y=1.01)
    fig.tight_layout()

    out = FIG_DIR / f"{key}_class_avgs_std.png"
    fig.savefig(str(out), dpi=150, bbox_inches="tight", facecolor="0.1")
    plt.close(fig)
    print(f"  -> {out.relative_to(REPO)}")
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--pkg", help="Only generate for this package key (e.g. dynamo)")
    args = ap.parse_args()

    pkgs = PACKAGES
    if args.pkg:
        pkgs = [p for p in PACKAGES if p["key"] == args.pkg.lower().replace("-", "")]
        if not pkgs:
            print(f"ERROR: unknown package key '{args.pkg}'")
            return 1

    generated = []
    for pkg in pkgs:
        out = make_panel(pkg)
        generated.append(out)

    print(f"\nDone. Generated {len(generated)} figure(s) in {FIG_DIR.relative_to(REPO)}/")
    for p in generated:
        print(f"  {p.name}")


if __name__ == "__main__":
    main()
