#!/usr/bin/env python3
"""
compute_t4p_fsc.py — Gold-standard FSC for T4P class averages vs unsplit baseline.

Computes half-set FSC for:
  1. Unsplit average (all 672 particles, even/odd halves)
  2. Dynamo ring_complete class (447p)
  3. Dynamo ring_altered class (225p)
  4. PyTom k=3 classes 0/1/2 (422/150/100p) — verifies which is junk

Outputs:
  packages/figures/T4P/fsc_comparison.png  — FSC curves figure
  results/T4P/fsc_summary.csv             — per-group resolution table

Usage:
  conda run -n eman2 python3 scripts/eval/compute_t4p_fsc.py
"""

import mrcfile
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
PARTICLE_DIR = REPO / "data" / "T4P_subtomos"
STD_DIR = REPO / "results" / "T4P"
FIG_DIR = REPO / "packages" / "figures" / "T4P"
FIG_DIR.mkdir(parents=True, exist_ok=True)

PIXEL_SIZE = 13.33   # Å/px for T4P
FSC_THRESHOLD_143 = 0.143
FSC_THRESHOLD_5 = 0.5


def load_mrc(path: Path) -> np.ndarray:
    with mrcfile.open(str(path), permissive=True) as mrc:
        return mrc.data.copy().astype(np.float32)


def half_set_averages(particle_paths: list) -> tuple:
    """Split paths into even/odd halves, return (half1_avg, half2_avg)."""
    half1_paths = particle_paths[0::2]
    half2_paths = particle_paths[1::2]

    def avg_vols(paths):
        acc = None
        for p in paths:
            if not p.exists():
                print(f"  WARNING: missing {p.name}")
                continue
            vol = load_mrc(p)
            acc = vol if acc is None else acc + vol
        return acc / len(paths) if acc is not None else None

    return avg_vols(half1_paths), avg_vols(half2_paths)


def fsc_3d(vol1: np.ndarray, vol2: np.ndarray) -> tuple:
    """Compute 3D FSC between two half-maps.

    Returns:
      freqs   : spatial frequencies in Å⁻¹  (length = box//2)
      fsc_arr : FSC values at each shell
    """
    box = vol1.shape[0]
    center = box // 2

    F1 = np.fft.fftshift(np.fft.fftn(vol1))
    F2 = np.fft.fftshift(np.fft.fftn(vol2))

    # Radial shell index for each voxel
    gz, gy, gx = np.mgrid[-center:center, -center:center, -center:center]
    r = np.round(np.sqrt(gx**2 + gy**2 + gz**2)).astype(int)

    freqs, fsc_arr = [], []
    for shell in range(1, center + 1):
        mask = r == shell
        if mask.sum() == 0:
            continue
        f1 = F1[mask]
        f2 = F2[mask]
        num = np.real(np.sum(f1 * np.conj(f2)))
        denom = np.sqrt(np.sum(np.abs(f1)**2) * np.sum(np.abs(f2)**2))
        fsc = float(num / denom) if denom > 0 else 0.0
        freq = shell / (box * PIXEL_SIZE)   # Å⁻¹
        freqs.append(freq)
        fsc_arr.append(fsc)

    return np.array(freqs), np.array(fsc_arr)


def resolution_at_threshold(freqs: np.ndarray, fsc_arr: np.ndarray,
                             threshold: float) -> float:
    """Return resolution (Å) where FSC first drops below threshold."""
    for i in range(len(fsc_arr)):
        if fsc_arr[i] < threshold:
            if i == 0:
                return float("inf")
            # Linear interpolation
            f0, f1 = freqs[i - 1], freqs[i]
            v0, v1 = fsc_arr[i - 1], fsc_arr[i]
            if v1 == v0:
                fq = (f0 + f1) / 2
            else:
                fq = f0 + (threshold - v0) * (f1 - f0) / (v1 - v0)
            return 1.0 / fq if fq > 0 else float("inf")
    # FSC never drops below threshold — resolution = Nyquist
    nyquist_freq = 0.5 / PIXEL_SIZE
    return 1.0 / nyquist_freq


def load_particles_for_class(std_csv: Path, class_int: int) -> list:
    """Return sorted list of particle Paths for a given class_int."""
    df = pd.read_csv(std_csv)
    fnames = df[df["class_int"] == class_int]["particle"].tolist()
    return [PARTICLE_DIR / f for f in fnames]


def compute_and_report(label: str, particle_paths: list) -> dict:
    """Compute half-set FSC for a particle list, print and return results dict."""
    n = len(particle_paths)
    print(f"\n  {label}  (n={n})")
    if n < 4:
        print(f"    Too few particles ({n}) — skipping")
        return {"label": label, "n": n,
                "res_ang_fsc0143": float("nan"), "res_ang_fsc05": float("nan")}

    h1, h2 = half_set_averages(particle_paths)
    if h1 is None or h2 is None:
        print("    ERROR: half-set averages are None")
        return {"label": label, "n": n,
                "res_ang_fsc0143": float("nan"), "res_ang_fsc05": float("nan")}

    freqs, fsc_arr = fsc_3d(h1, h2)
    res_143 = resolution_at_threshold(freqs, fsc_arr, FSC_THRESHOLD_143)
    res_5 = resolution_at_threshold(freqs, fsc_arr, FSC_THRESHOLD_5)
    nyquist = 2 * PIXEL_SIZE
    print(f"    FSC=0.143 → {res_143:.1f} Å   FSC=0.5 → {res_5:.1f} Å   "
          f"(Nyquist = {nyquist:.1f} Å)")
    return {"label": label, "n": n, "freqs": freqs, "fsc": fsc_arr,
            "res_ang_fsc0143": res_143, "res_ang_fsc05": res_5}


def main():
    # ------------------------------------------------------------------ #
    # 1. All 672 particles — unsplit baseline
    # ------------------------------------------------------------------ #
    all_particles = sorted(PARTICLE_DIR.glob("aligned_tom*.mrc"))
    print(f"Total T4P particles found: {len(all_particles)}")

    groups = []
    print("\n--- Unsplit baseline ---")
    groups.append(compute_and_report("Unsplit (672p)", all_particles))

    # ------------------------------------------------------------------ #
    # 2. Dynamo classes
    # ------------------------------------------------------------------ #
    dynamo_csv = STD_DIR / "dynamo_k2_std.csv"
    print("\n--- Dynamo k=2 classes ---")
    for class_int, label in [(1, "Dynamo ring_complete"), (2, "Dynamo ring_altered")]:
        paths = load_particles_for_class(dynamo_csv, class_int)
        groups.append(compute_and_report(label, paths))

    # ------------------------------------------------------------------ #
    # 3. PyTom k=3 classes — verify which is junk
    # ------------------------------------------------------------------ #
    pytom_csv = STD_DIR / "pytom_k3_std.csv"
    print("\n--- PyTom k=3 classes (junk verification) ---")
    pytom_label_map = {1: "PyTom class1 (ring_complete, 422p)",
                       2: "PyTom class2 (ring_altered, 150p)",
                       3: "PyTom class3 (junk?, 100p)"}
    pytom_groups = []
    for class_int, label in pytom_label_map.items():
        paths = load_particles_for_class(pytom_csv, class_int)
        r = compute_and_report(label, paths)
        pytom_groups.append(r)
    groups.extend(pytom_groups)

    # ------------------------------------------------------------------ #
    # 4. Figure — FSC curves
    # ------------------------------------------------------------------ #
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))

    nyquist_freq = 0.5 / PIXEL_SIZE
    x_ticks_ang = [80, 60, 40, 30, 27]

    # Panel 1: Unsplit vs Dynamo classes
    dynamo_colors = {"Unsplit (672p)": "gray",
                     "Dynamo ring_complete": "royalblue",
                     "Dynamo ring_altered": "tomato"}
    for g in groups[:3]:
        if "freqs" not in g:
            continue
        color = dynamo_colors.get(g["label"], "black")
        ax1.plot(g["freqs"], g["fsc"], label=g["label"], color=color, lw=2)

    ax1.axhline(FSC_THRESHOLD_143, color="k", ls="--", lw=1, label="FSC=0.143")
    ax1.axhline(FSC_THRESHOLD_5,   color="k", ls=":",  lw=1, label="FSC=0.5")
    ax1.axvline(nyquist_freq, color="0.6", ls="--", lw=1, label="Nyquist")
    ax1.set_xlabel("Spatial frequency (Å⁻¹)")
    ax1.set_ylabel("FSC")
    ax1.set_title("Unsplit vs Dynamo classes (T4P)")
    ax1.legend(fontsize=9)
    ax1.set_ylim(-0.1, 1.05)
    ax1.set_xlim(0, nyquist_freq * 1.02)
    ax1.grid(True, alpha=0.3)

    # Panel 2: PyTom k=3 junk verification
    pytom_colors = {1: "royalblue", 2: "tomato", 3: "gold"}
    for g, class_int in zip(pytom_groups, [1, 2, 3]):
        if "freqs" not in g:
            continue
        ax2.plot(g["freqs"], g["fsc"], label=g["label"],
                 color=pytom_colors[class_int], lw=2)

    ax2.axhline(FSC_THRESHOLD_143, color="k", ls="--", lw=1, label="FSC=0.143")
    ax2.axhline(FSC_THRESHOLD_5,   color="k", ls=":",  lw=1, label="FSC=0.5")
    ax2.axvline(nyquist_freq, color="0.6", ls="--", lw=1, label="Nyquist")
    ax2.set_xlabel("Spatial frequency (Å⁻¹)")
    ax2.set_ylabel("FSC")
    ax2.set_title("PyTom k=3 junk verification")
    ax2.legend(fontsize=9)
    ax2.set_ylim(-0.1, 1.05)
    ax2.set_xlim(0, nyquist_freq * 1.02)
    ax2.grid(True, alpha=0.3)

    fig.tight_layout()
    fsc_fig = FIG_DIR / "fsc_comparison.png"
    fig.savefig(str(fsc_fig), dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"\nFSC figure saved: {fsc_fig.relative_to(REPO)}")

    # ------------------------------------------------------------------ #
    # 5. Summary CSV
    # ------------------------------------------------------------------ #
    rows = []
    for g in groups:
        rows.append({
            "group": g["label"],
            "n_particles": g["n"],
            "res_ang_fsc0143": round(g["res_ang_fsc0143"], 1),
            "res_ang_fsc05": round(g["res_ang_fsc05"], 1),
        })

    out_csv = STD_DIR / "fsc_summary.csv"
    pd.DataFrame(rows).to_csv(str(out_csv), index=False)
    print(f"Summary CSV: {out_csv.relative_to(REPO)}")
    print("\nFull table:")
    print(pd.DataFrame(rows).to_string(index=False))

    # PyTom junk verdict
    print("\n--- PyTom junk class verdict ---")
    if len(pytom_groups) == 3 and all("res_ang_fsc0143" in g for g in pytom_groups):
        res = [g["res_ang_fsc0143"] for g in pytom_groups]
        n   = [g["n"] for g in pytom_groups]
        worst_class = int(np.argmax(res)) + 1
        print(f"  class1 (422p): {res[0]:.1f} Å  class2 (150p): {res[1]:.1f} Å  "
              f"class3 (100p): {res[2]:.1f} Å")
        if np.argmax(res) == 2:
            print(f"  VERDICT: class_int=3 (100p) has worst resolution ({res[2]:.1f} Å)"
                  " → confirmed junk")
        else:
            print(f"  VERDICT: class_int={worst_class} has worst resolution — "
                  "junk may not be class 3; inspect visually")


if __name__ == "__main__":
    main()
