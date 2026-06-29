#!/usr/bin/env python3
"""
standardize_t4p_results.py — produce uniform per-particle result CSVs for all T4P packages.

All raw package CSVs have different column names, ID types, and label conventions. This
script reads each raw CSV and outputs a standardized version with consistent columns:

  particle    — MRC filename (aligned_tom*.mrc), same for all packages
  class_int   — integer: 1=signal_a, 2=signal_b, [3=junk if present]
  class_name  — semantic label:
                  converging pkgs → ring_complete / ring_altered / junk
                  non-converging  → class_a / class_b / junk

Converging packages (Dynamo/PEET/PyTom/ProTomo) have their labels aligned to PEET via
Hungarian matching so class_int=1 always maps to ring_complete across all of them.

EMAN2 uses a 0-based particle_index instead of filename. The mapping is:
  particle_index=i → sorted(glob("aligned_tom*.mrc"))[i]   (verified from make_project.py)

Output: results/T4P/<pkg>_k<k>_std.csv  (one file per package)

Run:
  conda run -n eman2 python3 scripts/eval/standardize_t4p_results.py
"""

import csv
import os
from pathlib import Path

import numpy as np
from scipy.optimize import linear_sum_assignment

REPO = Path(__file__).resolve().parents[2]
OUT_DIR = REPO / "results" / "T4P"
OUT_DIR.mkdir(parents=True, exist_ok=True)

PEET_REF_CSV = REPO / "packages/peet/T4P/results/peet_final_class_assignments_v2.csv"

# ── label sets ────────────────────────────────────────────────────────────────
SEMANTIC  = {1: "ring_complete", 2: "ring_altered", 3: "junk"}
GENERIC   = {1: "class_a",       2: "class_b",      3: "junk"}


# ── loaders ───────────────────────────────────────────────────────────────────
def load_csv_by_name(path, id_col, class_col) -> dict:
    """Returns {filename: class_int}."""
    data = {}
    with open(path) as f:
        for row in csv.DictReader(f):
            data[row[id_col]] = int(row[class_col])
    return data


def load_eman2(path, sorted_particles) -> dict:
    """EMAN2 uses 0-based integer index; map to sorted filenames."""
    data = {}
    with open(path) as f:
        for row in csv.DictReader(f):
            idx = int(row["particle_index"])
            fname = sorted_particles[idx]
            data[fname] = int(row["class"])
    return data


# ── helpers ───────────────────────────────────────────────────────────────────
def hungarian_remap(pkg_data: dict, ref_data: dict, signal_classes: list) -> dict:
    """Return {old_class: new_class} permutation that maximises agreement with ref.

    Only signal_classes are permuted; junk (3) is passed through unchanged.
    """
    ref_signal = [1, 2]
    shared = {p for p in pkg_data if p in ref_data
              and pkg_data[p] in signal_classes
              and ref_data[p] in ref_signal}

    cost = np.zeros((len(signal_classes), len(ref_signal)))
    for i, sc in enumerate(signal_classes):
        for j, rc in enumerate(ref_signal):
            cost[i, j] = sum(1 for p in shared
                             if pkg_data[p] == sc and ref_data[p] == rc)
    ri, ci = linear_sum_assignment(-cost)
    mapping = {signal_classes[r]: ref_signal[c] for r, c in zip(ri, ci)}
    return mapping


def write_std(out_path, data: dict, sorted_particles, label_map: dict, names: dict,
              junk_classes: set):
    """Write standardised CSV; junk_classes are any raw labels to call class_int=3."""
    with open(out_path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["particle", "class_int", "class_name"])
        for fname in sorted_particles:
            raw = data.get(fname)
            if raw is None:
                continue
            if raw in junk_classes:
                class_int = 3
            else:
                class_int = label_map.get(raw, raw)
            class_name = names.get(class_int, f"class_{class_int}")
            w.writerow([fname, class_int, class_name])
    print(f"  -> {out_path.relative_to(REPO)}")


# ── main ──────────────────────────────────────────────────────────────────────
def main():
    # Load PEET as reference (sorted filenames + labels)
    peet_raw = load_csv_by_name(PEET_REF_CSV, "particle", "class")
    sorted_particles = sorted(peet_raw.keys())   # 672 filenames alphabetically
    assert len(sorted_particles) == 672, f"Expected 672 particles, got {len(sorted_particles)}"

    # ── Package configs ────────────────────────────────────────────────────────
    # converged: True  → Hungarian-align to PEET, use semantic names
    # converged: False → sort by class size, use generic names
    packages = [
        dict(
            name="peet", k=3, converged=True,
            data=load_csv_by_name(PEET_REF_CSV, "particle", "class"),
            signal_classes=[1, 2], junk_classes={3},
        ),
        dict(
            name="dynamo", k=2, converged=True,
            data=load_csv_by_name(
                REPO / "packages/dynamo/T4P/results/dynamo_final_results/class_assignments.csv",
                "particle", "class"),
            signal_classes=[1, 2], junk_classes=set(),
            note="k=2 only — junk class pending re-run at k=3",
        ),
        dict(
            name="pytom", k=3, converged=True,
            data=load_csv_by_name(REPO / "results/pytom_v2mask_k3.csv", "file", "pred_label"),
            # k=3: 422/150/100; class 2 (100p, smallest) assumed junk — verify by FSC
            signal_classes=[0, 1], junk_classes={2},
            note="junk class = class 2 (100 particles, smallest); verify by FSC inspection",
        ),
        dict(
            name="protomo", k=3, converged=True,
            data=load_csv_by_name(REPO / "results/protomo_T4P_k3.csv", "file", "pred_label"),
            # ProTomo raw: 0=signal_a, 1=signal_b, 2=junk
            signal_classes=[0, 1], junk_classes={2},
        ),
        dict(
            name="eman2", k=3, converged=False,
            data=load_eman2(
                REPO / "packages/eman2/T4P/results/eman2_T4P_k3_none_r01_assignments.csv",
                sorted_particles),
            # EMAN2 PCA splits on contrast axis (not conformation); class 3 = PCA outliers/junk
            signal_classes=[1, 2], junk_classes={3},
        ),
        dict(
            name="disca", k=2, converged=False,
            data=load_csv_by_name(REPO / "results/disca_cyl_v2_k2.csv", "file", "pred_label"),
            signal_classes=[0, 1], junk_classes=set(),
            note="k=2 only — junk class pending re-run at k=3",
        ),
        dict(
            name="opus", k=2, converged=False,
            data=load_csv_by_name(REPO / "results/opus_tomo_k2.csv", "file", "pred_label"),
            signal_classes=[0, 1], junk_classes=set(),
            note="k=2 only — junk class pending re-run at k=3",
        ),
        # STOPGAP: no per-particle class CSV (only PCA eigenfactors) — Eben's
        # RELION:  algorithm-level collapse → not standardised (all one class)
        # TomoFlow: no per-particle class assignment CSV
    ]

    for pkg in packages:
        name = pkg["name"]
        converged = pkg["converged"]
        signal_classes = pkg["signal_classes"]
        junk_classes = pkg["junk_classes"]
        data = pkg["data"]
        k = pkg["k"]
        note = pkg.get("note", "")

        print(f"\n[{name}] k={k}, converged={converged}")
        if note:
            print(f"  NOTE: {note}")

        # Count per class
        from collections import Counter
        counts = Counter(data.values())
        for cls, cnt in sorted(counts.items()):
            tag = " (junk)" if cls in junk_classes else ""
            print(f"  raw class {cls}: {cnt} particles{tag}")

        if converged:
            # Hungarian-align signal classes to PEET reference
            label_map = hungarian_remap(data, peet_raw, signal_classes)
            names = SEMANTIC
        else:
            # Sort signal classes by size (largest=1) — no semantic correspondence
            sorted_by_size = sorted(
                [(cls, sum(1 for v in data.values() if v == cls)) for cls in signal_classes],
                key=lambda x: -x[1]
            )
            label_map = {cls: i+1 for i, (cls, _) in enumerate(sorted_by_size)}
            names = GENERIC

        # Junk always → 3
        for jc in junk_classes:
            label_map[jc] = 3

        print(f"  label remap: {label_map}")

        out_path = OUT_DIR / f"{name}_k{k}_std.csv"
        write_std(out_path, data, sorted_particles, label_map, names, junk_classes)

        # Count output
        with open(out_path) as f:
            rows = list(csv.DictReader(f))
        out_counts = Counter(r["class_name"] for r in rows)
        print(f"  output: {dict(out_counts)}")

    print(f"\nDone. Standardised CSVs in results/T4P/")


if __name__ == "__main__":
    main()
