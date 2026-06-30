#!/usr/bin/env python3
"""
gen_t4p_full_pkg_grid.py — All-10-package cross-package ARI grid for T4P.

Shows all packages in one figure, making the exclusion criteria explicit:
  • Converging (structural axis): 4 packages that find the same 2-class split
  • Non-structural split: packages that produce a partition, but on contrast/
    intensity axes (confirmed by FM_easy confusion matrices showing no diagonal)
  • Collapsed: packages whose output is a degenerate 1- or near-1-class partition

9 of 10 packages have per-particle CSVs and appear in the N×N ARI grid.
TomoFlow has no CSV (result recorded as class sizes only: k=2 → 638/34).

ARI is computed on the intersection of non-junk particles for each pair
(junk = class_int 3, excluded before comparison). This is the standard
approach for benchmarks where different packages use different k.

Usage (from repo root):
  conda run -n eman2 python3 scripts/eval/gen_t4p_full_pkg_grid.py \
      [--out packages/figures/T4P/all_pkg_grid.png]
"""
import argparse
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from pathlib import Path
from sklearn.metrics import adjusted_rand_score

REPO = Path(__file__).resolve().parents[2]
STD = REPO / "results" / "T4P"

# ──────────────────────────────────────────────────────────────
# Package registry: ordered converging → non-structural → collapsed
# ──────────────────────────────────────────────────────────────
PKGS = [
    # --- Converging: structural axis; same split found independently ---
    dict(name="Dynamo",   csv="dynamo_k2_std.csv",  cat="converging",
         note="447 / 225"),
    dict(name="PEET",     csv="peet_k3_std.csv",    cat="converging",
         note="374 / 230 / 68 junk"),
    dict(name="PyTom",    csv="pytom_k3_std.csv",   cat="converging",
         note="422 / 150 / 100 junk"),
    dict(name="ProTomo",  csv="protomo_k3_std.csv", cat="converging",
         note="334 / 212 / 126 junk"),
    # --- Non-structural split: partition produced, but wrong axis ---
    dict(name="DISCA",    csv="disca_k3_std.csv",   cat="non_structural",
         note="315 / 267 / 90 junk\ncontrast axis (confirmed FM_easy)"),
    dict(name="OPUS",     csv="opus_k3_std.csv",    cat="non_structural",
         note="368 / 221 / 83 junk\ncontrast axis (confirmed FM_easy)"),
    dict(name="EMAN2",    csv="eman2_k3_std.csv",   cat="non_structural",
         note="317 / 270 / 85 junk\ncontrast axis (confirmed FM_easy)"),
    dict(name="STOPGAP",  csv="stopgap_k2_std.csv", cat="non_structural",
         note="385 / 287\nno discrete gap in PCA space"),
    # --- Collapsed: degenerate partition (1 dominant class) ---
    dict(name="RELION",   csv="relion_k2_std.csv",  cat="collapsed",
         note="16 / 656\nsoft-EM smooths signal away\n(ARI≈0 on FM_easy too)"),
    # TomoFlow: no per-particle CSV; class sizes only
    dict(name="TomoFlow", csv=None,                 cat="collapsed",
         note="638 / 34  (k=2)\n95% one class; no per-particle output"),
]

CAT_COLOR = {
    "converging":      "#2ca02c",   # green
    "non_structural":  "#ff7f0e",   # orange
    "collapsed":       "#d62728",   # red
}
CAT_LABEL = {
    "converging":      "Converging\n(structural axis)",
    "non_structural":  "Non-structural split\n(contrast / no-gap axis)",
    "collapsed":       "Collapsed\n(degenerate partition)",
}


def load_series(pkg: dict) -> pd.Series | None:
    if pkg["csv"] is None:
        return None
    p = STD / pkg["csv"]
    if not p.exists():
        print(f"  WARNING: {pkg['name']} CSV not found: {p}")
        return None
    df = pd.read_csv(p)
    s = df.set_index("particle")["class_int"].astype(float)
    return s[s != 3]   # exclude junk


def pairwise_ari(sA: pd.Series, sB: pd.Series) -> tuple[float, int]:
    shared = sA.index.intersection(sB.index)
    if len(shared) < 10:
        return float("nan"), len(shared)
    ari = adjusted_rand_score(sA.loc[shared].values, sB.loc[shared].values)
    return ari, len(shared)


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", default="packages/figures/T4P/all_pkg_grid.png")
    args = ap.parse_args()

    # Load series for all packages with CSVs
    for pkg in PKGS:
        pkg["series"] = load_series(pkg)

    # Packages with per-particle data (for the grid)
    grid_pkgs = [p for p in PKGS if p["series"] is not None]
    no_csv_pkgs = [p for p in PKGS if p["series"] is None]
    n = len(grid_pkgs)

    print(f"\nBuilding {n}×{n} ARI grid + {len(no_csv_pkgs)} no-CSV packages\n")

    # Compute full ARI matrix
    ari_mat = np.full((n, n), np.nan)
    n_mat = np.zeros((n, n), dtype=int)
    for i in range(n):
        for j in range(n):
            if i == j:
                ari_mat[i, j] = 1.0
                n_mat[i, j] = int(grid_pkgs[i]["series"].notna().sum())
            else:
                ari, cnt = pairwise_ari(grid_pkgs[i]["series"], grid_pkgs[j]["series"])
                ari_mat[i, j] = ari
                n_mat[i, j] = cnt

    # Print summary
    print("Pairwise ARI (non-junk intersection):")
    for i in range(n):
        for j in range(i+1, n):
            a, b = grid_pkgs[i]["name"], grid_pkgs[j]["name"]
            print(f"  {a:10s} vs {b:10s}: ARI={ari_mat[i,j]:.3f}  n={n_mat[i,j]}")

    # ──────────────────────────────────────────────────────────
    # Figure layout: left = N×N grid; right = no-CSV summary
    # ──────────────────────────────────────────────────────────
    fig = plt.figure(figsize=(14, 11))

    # Main grid axes (left 75%)
    ax_grid = fig.add_axes([0.08, 0.20, 0.62, 0.72])

    # Right sidebar (no-CSV packages)
    ax_side = fig.add_axes([0.73, 0.20, 0.24, 0.72])
    ax_side.axis("off")

    # Bottom legend strip
    ax_leg = fig.add_axes([0.08, 0.03, 0.88, 0.14])
    ax_leg.axis("off")

    # ── ARI heatmap ──
    # NaN for diagonal becomes 1; clamp to [−0.1, 1] for color
    display = np.where(np.isnan(ari_mat), 0.0, ari_mat)
    im = ax_grid.imshow(display, vmin=-0.1, vmax=1.0, cmap="RdYlGn", aspect="auto")

    # Axes ticks / labels — color-coded by category
    names = [p["name"] for p in grid_pkgs]
    cats  = [p["cat"]  for p in grid_pkgs]

    ax_grid.set_xticks(range(n))
    ax_grid.set_xticklabels(names, rotation=45, ha="right", fontsize=9)
    ax_grid.set_yticks(range(n))
    ax_grid.set_yticklabels(names, fontsize=9)

    for tick, cat in zip(ax_grid.get_xticklabels(), cats):
        tick.set_color(CAT_COLOR[cat])
        tick.set_fontweight("bold")
    for tick, cat in zip(ax_grid.get_yticklabels(), cats):
        tick.set_color(CAT_COLOR[cat])
        tick.set_fontweight("bold")

    # Separator lines between categories
    cat_boundaries = []
    for i in range(1, n):
        if cats[i] != cats[i-1]:
            cat_boundaries.append(i - 0.5)
    for b in cat_boundaries:
        ax_grid.axhline(b, color="white", linewidth=2.5)
        ax_grid.axvline(b, color="white", linewidth=2.5)

    # Cell annotations: ARI value + n_shared
    for i in range(n):
        for j in range(n):
            val = ari_mat[i, j]
            ns  = n_mat[i, j]
            if i == j:
                ax_grid.text(j, i, f"—", ha="center", va="center",
                             fontsize=10, color="0.4")
            elif np.isnan(val):
                ax_grid.text(j, i, "N/A", ha="center", va="center",
                             fontsize=8, color="0.5")
            else:
                bg = display[i, j]
                txt_color = "white" if (bg > 0.65 or bg < -0.05) else "black"
                # Show values near 0 without spurious ± sign
                label = f"{val:.3f}" if abs(val) >= 0.005 else "≈0"
                ax_grid.text(j, i, label, ha="center", va="center",
                             fontsize=8, color=txt_color, fontweight="bold")
                ax_grid.text(j, i + 0.30, f"n={ns}", ha="center", va="center",
                             fontsize=6, color=txt_color if txt_color == "white" else "0.4")

    cbar = fig.colorbar(im, ax=ax_grid, fraction=0.035, pad=0.01)
    cbar.set_label("ARI (adjusted Rand index)", fontsize=8)
    cbar.ax.tick_params(labelsize=7)

    ax_grid.set_title(
        "T4P — Pairwise ARI: all packages with per-particle output\n"
        "(junk class excluded; ARI on non-junk intersection per pair)\n"
        "Key finding: DISCA/OPUS/EMAN2 agree with each other (ARI 0.88–1.00) but not "
        "with converging packages (ARI ≈ 0) — different axes, not the same split.",
        fontsize=9, pad=8
    )

    # ── Right sidebar: no-CSV packages ──
    ax_side.text(0.5, 0.97, "No per-particle\noutput", ha="center", va="top",
                 fontsize=10, fontweight="bold", color=CAT_COLOR["collapsed"],
                 transform=ax_side.transAxes)
    y = 0.88
    for pkg in no_csv_pkgs:
        ax_side.text(0.5, y, pkg["name"], ha="center", va="top",
                     fontsize=10, fontweight="bold", color=CAT_COLOR[pkg["cat"]],
                     transform=ax_side.transAxes)
        y -= 0.06
        for line in pkg["note"].split("\n"):
            ax_side.text(0.5, y, line, ha="center", va="top",
                         fontsize=7.5, color="0.3", transform=ax_side.transAxes)
            y -= 0.05
        y -= 0.04
    ax_side.set_xlim(0, 1); ax_side.set_ylim(0, 1)
    ax_side.add_patch(mpatches.FancyBboxPatch(
        (0.02, 0.02), 0.96, 0.96, boxstyle="round,pad=0.02",
        linewidth=1.5, edgecolor=CAT_COLOR["collapsed"], facecolor="#fff0f0",
        transform=ax_side.transAxes, clip_on=False))

    # ── Bottom legend ──
    legend_text = (
        "■  Converging (structural axis, green): 4 packages independently find the same 2-class split "
        "(pairwise ARI 0.40–0.65). Evidence that the split reflects real structure.\n"
        "■  Non-structural split (orange): partition produced, but on contrast / intensity / no-gap PCA axis — "
        "confirmed by FM_easy confusion matrices (no diagonal at known GT).\n"
        "■  Collapsed (red): output is a degenerate 1- or near-1-class partition. "
        "RELION soft-EM and TomoFlow both collapse even when GT-seeded on FM_easy.\n"
        "ARI = 0 means no agreement beyond chance; ARI = 1 means identical assignments. "
        "Near-zero ARI between converging and non-structural packages is expected — "
        "they are finding different structure, not the same one."
    )
    ax_leg.text(0.01, 0.95, legend_text, ha="left", va="top",
                fontsize=7.5, color="0.2", transform=ax_leg.transAxes,
                wrap=True, multialignment="left")
    for cat, color in CAT_COLOR.items():
        pass  # colors explained in text above

    # Category color patches in legend
    patch_y = 0.50
    for cat, color in CAT_COLOR.items():
        ax_leg.add_patch(mpatches.Rectangle((0.01, patch_y - 0.08), 0.012, 0.09,
                                             facecolor=color, edgecolor="none",
                                             transform=ax_leg.transAxes))
        ax_leg.text(0.027, patch_y - 0.01, CAT_LABEL[cat].replace("\n", " — "),
                    ha="left", va="center", fontsize=7.5, color=color,
                    fontweight="bold", transform=ax_leg.transAxes)
        patch_y -= 0.16

    fig.suptitle("T4P — All 10 Packages: Classification Agreement Grid",
                 fontsize=12, fontweight="bold", y=0.995)

    out = REPO / args.out
    out.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"\nSaved: {out}")


if __name__ == "__main__":
    main()
