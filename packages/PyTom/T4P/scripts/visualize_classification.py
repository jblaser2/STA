#!/usr/bin/env python3
"""
visualize_classification.py

Visualize results from a PyTom auto-focus classification run.

Reads the final iteration's output from the classification output directory
and produces:

  clustering_map.png
      Bar chart of particle counts per class (and noise class -1 if present).

  class_<N>_central_slice.png  (one per non-noise class)
      Two orthogonal central slices of each final class-average EM volume:
        Left  - XZ cross-section at central Y  (pilus end-on / transverse view)
        Right - XY slice at central Z           (pilus side / longitudinal view)

Usage:
    python visualize_classification.py --output_dir ./autofocus_output/
    python visualize_classification.py --output_dir ./autofocus_output/ --save_dir ./figures/
"""

import os
import sys
import glob
import struct
import argparse
import numpy as np
import xml.etree.ElementTree as ET


# ---------------------------------------------------------------------------
# EM file I/O
# ---------------------------------------------------------------------------

def read_em(filename: str) -> np.ndarray:
    """
    Read a PyTom EM-format volume.

    Returns a float32 numpy array of shape (nz, ny, nx).
    EM stores data with x varying fastest, which is equivalent to
    C-order for the (nz, ny, nx) shape (last axis = x is fastest).
    """
    with open(filename, 'rb') as f:
        header = f.read(512)
        nx = struct.unpack_from('<i', header, 4)[0]
        ny = struct.unpack_from('<i', header, 8)[0]
        nz = struct.unpack_from('<i', header, 12)[0]
        dtype_code = struct.unpack_from('<i', header, 16)[0]
        dtype_map = {1: np.int8, 2: np.int16, 4: np.int32,
                     5: np.float32, 9: np.float64}
        dtype = dtype_map.get(dtype_code, np.float32)
        raw = np.frombuffer(f.read(), dtype=dtype)
    return raw.reshape(nz, ny, nx).copy()


# ---------------------------------------------------------------------------
# XML parsing
# ---------------------------------------------------------------------------

def parse_class_counts(xml_file: str) -> dict:
    """
    Parse a classified PyTom ParticleList XML.
    Returns {class_label_str: particle_count}.
    """
    tree = ET.parse(xml_file)
    root = tree.getroot()
    counts: dict = {}
    for particle in root.findall('Particle'):
        cls_elem = particle.find('Class')
        label = cls_elem.get('Name', '0') if cls_elem is not None else '0'
        counts[label] = counts.get(label, 0) + 1
    return counts


def find_last_iteration(output_dir: str):
    """
    Find the highest-numbered classified_pl_iter*.xml in output_dir.
    Returns (xml_path, iteration_number) or (None, None).
    """
    xmls = glob.glob(os.path.join(output_dir, 'classified_pl_iter*.xml'))
    if not xmls:
        return None, None

    def iter_num(f):
        base = os.path.basename(f)
        return int(base.replace('classified_pl_iter', '').replace('.xml', ''))

    xmls.sort(key=iter_num)
    last_xml = xmls[-1]
    return last_xml, iter_num(last_xml)


# ---------------------------------------------------------------------------
# Plotting
# ---------------------------------------------------------------------------

def plot_clustering_map(counts: dict, output_path: str) -> None:
    """Bar chart of particle counts per class."""
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt

    # Sort: numbered classes first, noise class -1 last
    labels = sorted(counts.keys(), key=lambda x: (x == '-1', int(x) if x != '-1' else 999))
    values = [counts[l] for l in labels]

    palette = plt.cm.tab10.colors
    colors = []
    ci = 0
    for l in labels:
        if l == '-1':
            colors.append('#d9534f')  # red for noise
        else:
            colors.append(palette[ci % len(palette)])
            ci += 1

    fig, ax = plt.subplots(figsize=(max(6, len(labels) * 1.5), 5))
    bars = ax.bar(labels, values, color=colors, edgecolor='black', linewidth=0.8)

    for bar, val in zip(bars, values):
        ax.text(bar.get_x() + bar.get_width() / 2,
                bar.get_height() + max(values) * 0.01,
                str(val), ha='center', va='bottom',
                fontsize=12, fontweight='bold')

    ax.set_xlabel('Class Label', fontsize=13)
    ax.set_ylabel('Number of Particles', fontsize=13)
    ax.set_title('T4P Classification: Particle Distribution Across Classes',
                 fontsize=13, fontweight='bold')
    ax.set_ylim(0, max(values) * 1.15)

    total = sum(values)
    note = f'Total: {total} particles'
    if '-1' in counts:
        note += '   |   Red = noise class (−1)'
    ax.text(0.98, 0.97, note, transform=ax.transAxes,
            ha='right', va='top', fontsize=10, color='#555555')

    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"  Saved: {output_path}")


def plot_class_slices(em_file: str, class_label: str, output_path: str) -> None:
    """
    Two orthogonal central slices of a class-average EM volume.

    vol shape: (nz, ny, nx)   -- Y is the pilus/filament axis

    Left panel  : XZ cross-section at central Y  (vol[:, ny//2, :])
                  Shows the pilus end-on / transverse structure.
    Right panel : XY view at central Z            (vol[nz//2, :, :])
                  Shows the pilus side / longitudinal structure.
    """
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt

    vol = read_em(em_file)          # (nz, ny, nx)
    nz, ny, nx = vol.shape
    cy, cz = ny // 2, nz // 2

    xz_slice = vol[:, cy, :]        # shape (nz, nx) -- transverse
    xy_slice = vol[cz, :, :]        # shape (ny, nx) -- longitudinal

    vmin, vmax = np.percentile(vol, [2, 98])

    fig, axes = plt.subplots(1, 2, figsize=(11, 5))
    fig.suptitle(f'Class {class_label}  —  Final Class Average  ({nz}x{ny}x{nx} vox)',
                 fontsize=13, fontweight='bold')

    kw = dict(cmap='gray', origin='lower', vmin=vmin, vmax=vmax, aspect='equal')

    im0 = axes[0].imshow(xz_slice, **kw)
    axes[0].set_title('XZ cross-section (at central Y)\nPilus end-on / transverse view',
                       fontsize=11)
    axes[0].set_xlabel('X  (voxels)')
    axes[0].set_ylabel('Z  (voxels)')
    plt.colorbar(im0, ax=axes[0], fraction=0.046, pad=0.04)

    im1 = axes[1].imshow(xy_slice, **kw)
    axes[1].set_title('XY longitudinal (at central Z)\nPilus side view  [Y = filament axis]',
                       fontsize=11)
    axes[1].set_xlabel('X  (voxels)')
    axes[1].set_ylabel('Y  (voxels)  —  pilus axis')
    plt.colorbar(im1, ax=axes[1], fraction=0.046, pad=0.04)

    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"  Saved: {output_path}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description='Visualize PyTom auto-focus classification results.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__)
    parser.add_argument('--output_dir', required=True,
                        help='Directory containing classification output files '
                             '(classified_pl_iter*.xml, iter*_class*.em)')
    parser.add_argument('--save_dir', default=None,
                        help='Directory to save PNG files (default: same as output_dir)')
    args = parser.parse_args()

    output_dir = os.path.abspath(args.output_dir)
    save_dir   = os.path.abspath(args.save_dir) if args.save_dir else output_dir
    os.makedirs(save_dir, exist_ok=True)

    print(f"Reading results from : {output_dir}")
    print(f"Saving figures to    : {save_dir}")

    # Locate last iteration
    last_xml, last_iter = find_last_iteration(output_dir)
    if last_xml is None:
        print("ERROR: No classified_pl_iter*.xml files found in output directory.")
        sys.exit(1)

    print(f"Last iteration       : {last_iter}  ({os.path.basename(last_xml)})")

    # Parse and report class counts
    counts = parse_class_counts(last_xml)
    print(f"\nClass distribution:")
    total = sum(counts.values())
    for label in sorted(counts, key=lambda x: (x == '-1', int(x) if x != '-1' else 999)):
        pct = 100.0 * counts[label] / total
        tag = '  <-- noise' if label == '-1' else ''
        print(f"  Class {label:>4s} : {counts[label]:5d} particles  ({pct:.1f}%){tag}")

    # 1. Clustering map
    print("\nGenerating clustering map...")
    plot_clustering_map(counts, os.path.join(save_dir, 'clustering_map.png'))

    # 2. Central slices for each non-noise class
    class_labels = sorted(
        [l for l in counts if l != '-1'],
        key=lambda x: int(x) if x.lstrip('-').isdigit() else 0)

    print("\nGenerating central slice figures...")
    for label in class_labels:
        em_file = os.path.join(output_dir, f'iter{last_iter}_class{label}.em')
        if not os.path.exists(em_file):
            print(f"  WARNING: not found -- {em_file}")
            continue
        out_png = os.path.join(save_dir, f'class_{label}_central_slice.png')
        plot_class_slices(em_file, label, out_png)

    print(f"\nAll figures saved to: {save_dir}")


if __name__ == '__main__':
    main()
