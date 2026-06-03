#!/usr/bin/env python3
"""
Compute a mask-normalized subtomogram average and compare to the starting average.

Each subtomogram is z-score normalized using statistics computed only from voxels
inside the cylindrical T4P mask, so bright/dark out-of-mask objects cannot skew the
contrast stretch. All 672 normalized volumes are then averaged.

Outputs:
  STA/masked_average.mrc         — the new average (raw float32 MRC)
  STA/masked_average_comparison.png — side-by-side comparison figure
"""

from pathlib import Path
import numpy as np
import mrcfile
import matplotlib
matplotlib.use("TkAgg")
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec

STA_DIR         = Path(__file__).parent
SUBTOMOS_DIR    = STA_DIR / "subtomos_mrc"
MASK_PATH       = STA_DIR / "T4P_mask" / "cylindrical_mask.npy"
REF_AVG_PATH    = STA_DIR / "PyTom" / "starting_average.mrc"
OUT_MRC         = STA_DIR / "masked_average.mrc"
OUT_PNG         = STA_DIR / "masked_average_comparison.png"
HALF_SLAB       = 5   # slices averaged each side of center for display


def normalize_slice(sl):
    """Robust percentile stretch for display (2nd–98th)."""
    p2, p98 = np.percentile(sl, (2, 98))
    if p98 == p2:
        return np.zeros_like(sl, dtype=float)
    return np.clip((sl.astype(float) - p2) / (p98 - p2), 0, 1)


def slab_views(vol):
    """Return normalized central Z, Y, X average-slab projections."""
    nz, ny, nx = vol.shape
    cz, cy, cx = nz // 2, ny // 2, nx // 2
    z = normalize_slice(vol[max(0, cz-HALF_SLAB):cz+HALF_SLAB].mean(axis=0))
    y = normalize_slice(vol[:, max(0, cy-HALF_SLAB):cy+HALF_SLAB].mean(axis=1))
    x = normalize_slice(vol[:, :, max(0, cx-HALF_SLAB):cx+HALF_SLAB].mean(axis=2))
    return z, y, x


def main():
    # ── Load mask ─────────────────────────────────────────────────────────────
    mask = np.load(MASK_PATH).astype(bool)
    n_mask_voxels = mask.sum()
    print(f"Mask loaded: {mask.shape}, {n_mask_voxels} active voxels ({100*n_mask_voxels/mask.size:.2f}%)")

    # ── Collect subtomograms ───────────────────────────────────────────────────
    mrc_files = sorted(SUBTOMOS_DIR.glob("*.mrc"))
    n = len(mrc_files)
    print(f"Subtomograms found: {n}")

    accumulator = np.zeros((80, 80, 80), dtype=np.float64)
    skipped = 0

    for i, path in enumerate(mrc_files, 1):
        if i % 50 == 0 or i == n:
            print(f"  Averaging: {i}/{n}", flush=True)

        with mrcfile.open(str(path), mode='r', permissive=True) as f:
            vol = f.data.astype(np.float64)

        in_mask = vol[mask]
        mu = in_mask.mean()
        sigma = in_mask.std()

        if sigma < 1e-9:
            skipped += 1
            continue

        normed = (vol - mu) / sigma
        accumulator += normed

    valid = n - skipped
    if valid == 0:
        print("ERROR: No valid subtomograms.")
        return

    masked_avg = (accumulator / valid).astype(np.float32)
    print(f"Averaged {valid} subtomograms ({skipped} skipped — zero variance in mask).")

    # ── Save MRC ──────────────────────────────────────────────────────────────
    with mrcfile.new(str(OUT_MRC), overwrite=True) as f:
        f.set_data(masked_avg)
    print(f"Saved: {OUT_MRC}")

    # ── Load reference average ────────────────────────────────────────────────
    with mrcfile.open(str(REF_AVG_PATH), mode='r', permissive=True) as f:
        ref_avg = f.data.astype(np.float32)

    # ── Quantitative comparison ───────────────────────────────────────────────
    ref_std_in  = ref_avg[mask].std()
    new_std_in  = masked_avg[mask].std()
    ref_std_out = ref_avg[~mask].std()
    new_std_out = masked_avg[~mask].std()

    ref_snr = ref_std_in / ref_std_out if ref_std_out > 0 else float("nan")
    new_snr = new_std_in / new_std_out if new_std_out > 0 else float("nan")

    print()
    print("In-mask std  (higher = more detail in pilus):")
    print(f"  starting_average : {ref_std_in:.4f}")
    print(f"  masked_average   : {new_std_in:.4f}")
    print()
    print("In-mask / out-mask std ratio  (higher = better pilus SNR):")
    print(f"  starting_average : {ref_snr:.4f}")
    print(f"  masked_average   : {new_snr:.4f}")
    print(f"  improvement      : {new_snr/ref_snr:.3f}x" if ref_snr > 0 else "  (reference ratio unavailable)")

    # ── Comparison figure ─────────────────────────────────────────────────────
    fig = plt.figure(figsize=(13, 9))
    fig.patch.set_facecolor("#1a1a2e")

    gs = gridspec.GridSpec(3, 3, figure=fig, wspace=0.05, hspace=0.15,
                           left=0.03, right=0.97, top=0.92, bottom=0.04)

    rows = [
        ("Starting average\n(full-volume normalization)", ref_avg,    "#aaaaff"),
        ("Masked average\n(pilus-region normalization)",  masked_avg, "#44ff88"),
        ("Difference  (masked − starting)",               masked_avg - ref_avg, "#ffaa44"),
    ]

    col_labels = ["Z slab (axial)", "Y slab (coronal)", "X slab (sagittal)"]

    for row_idx, (row_label, vol, label_color) in enumerate(rows):
        z_sl, y_sl, x_sl = slab_views(vol)
        for col_idx, sl in enumerate((z_sl, y_sl, x_sl)):
            ax = fig.add_subplot(gs[row_idx, col_idx])
            ax.set_facecolor("#0d0d1a")
            ax.tick_params(left=False, bottom=False, labelleft=False, labelbottom=False)
            for sp in ax.spines.values():
                sp.set_edgecolor("#444")

            ax.imshow(sl, cmap="gray", vmin=0, vmax=1, interpolation="nearest")

            # Green crosshair
            ax.axhline(39.5, color="#00ff55", lw=0.8, alpha=0.65, linestyle="--")
            ax.axvline(39.5, color="#00ff55", lw=0.8, alpha=0.65, linestyle="--")

            if col_idx == 0:
                ax.set_ylabel(row_label, color=label_color, fontsize=8,
                              rotation=90, labelpad=4)
            if row_idx == 0:
                ax.set_title(col_labels[col_idx], color="#aaa", fontsize=9)

    fig.suptitle(
        f"T4P subtomogram average comparison  (n={valid})\n"
        f"In-mask SNR: starting={ref_snr:.3f}  masked={new_snr:.3f}  "
        f"({new_snr/ref_snr:.2f}x improvement)" if ref_snr > 0 else "",
        color="white", fontsize=10
    )

    plt.savefig(str(OUT_PNG), dpi=150, bbox_inches="tight", facecolor=fig.get_facecolor())
    print(f"Saved: {OUT_PNG}")

    plt.show()


if __name__ == "__main__":
    main()
