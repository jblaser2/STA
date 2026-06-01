#!/usr/bin/env python3
"""Plot PCA scatter from STOPGAP eigenfac.star, colored by class label."""

import sys
import os
import itertools
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt


def read_star(path):
    """Parse a STOPGAP STAR file, returning {column: array}.

    Numeric columns are float arrays; string columns (e.g. halfset) are kept
    as object arrays. Handles files with a single loop_ block.
    """
    columns = []
    rows = []
    in_loop = False

    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            if line.startswith('data_'):
                in_loop = False
                columns = []
                rows = []
                continue
            if line == 'loop_':
                in_loop = True
                columns = []
                rows = []
                continue
            if in_loop and line.startswith('_'):
                columns.append(line.lstrip('_'))
                continue
            if in_loop and columns:
                rows.append(line.split())

    if not rows:
        raise ValueError(f'No data found in {path}')

    result = {}
    for i, col in enumerate(columns):
        col_vals = [row[i] for row in rows if i < len(row)]
        try:
            result[col] = np.array(col_vals, dtype=float)
        except ValueError:
            result[col] = np.array(col_vals)
    return result


def plot_pca_scatter(eigenfac_path, motl_path, out_dir, n_plot_pcs=4):
    os.makedirs(out_dir, exist_ok=True)

    ef   = read_star(eigenfac_path)
    motl = read_star(motl_path)

    # All columns in eigenfac.star are per-particle PC scores.
    # Take up to n_plot_pcs; label them PC1, PC2, ...
    pc_keys = list(ef.keys())[:n_plot_pcs]
    if not pc_keys:
        raise ValueError(f'eigenfac.star has no columns: {eigenfac_path}')
    scores = np.column_stack([ef[k] for k in pc_keys])

    if 'class' not in motl:
        raise KeyError("'class' column not found in motl file")
    classes   = motl['class'].astype(int)
    class_ids = sorted(set(classes))
    cmap      = plt.cm.get_cmap('tab10', max(len(class_ids), 3))

    n_pcs = scores.shape[1]
    print(f'Particles: {len(classes)}  |  Classes: {class_ids}  |  PCs: {n_pcs}')

    # Pairwise scatter plots
    for (i, j) in itertools.combinations(range(n_pcs), 2):
        fig, ax = plt.subplots(figsize=(6, 5))
        for c_idx, c in enumerate(class_ids):
            mask = classes == c
            ax.scatter(
                scores[mask, i], scores[mask, j],
                s=15, alpha=0.75, color=cmap(c_idx),
                label=f'Class {c}  (n={mask.sum()})'
            )
        ax.set_xlabel(f'PC{i + 1}', fontsize=12)
        ax.set_ylabel(f'PC{j + 1}', fontsize=12)
        ax.set_title(f'PCA: PC{i + 1} vs PC{j + 1}  (n={len(classes)} particles)')
        ax.legend(markerscale=2, framealpha=0.8, fontsize=9)
        ax.grid(True, alpha=0.3)
        ax.axhline(0, color='k', linewidth=0.5, alpha=0.4)
        ax.axvline(0, color='k', linewidth=0.5, alpha=0.4)
        fname = os.path.join(out_dir, f'pca_pc{i + 1}_vs_pc{j + 1}.png')
        fig.savefig(fname, dpi=150, bbox_inches='tight')
        plt.close(fig)
        print(f'Saved {fname}')

    # Scree plot from eigenval.star if present alongside eigenfac.star
    eigenval_path = os.path.join(os.path.dirname(eigenfac_path), 'eigenval.star')
    if os.path.exists(eigenval_path):
        ev = read_star(eigenval_path)
        ev_key = next((k for k in ev if 'eigenval' in k.lower()), None)
        if ev_key:
            vals = ev[ev_key]
            pct  = 100.0 * vals / vals.sum()
            cumulative = np.cumsum(pct)
            n_ev = len(vals)

            fig, ax1 = plt.subplots(figsize=(7, 4))
            ax1.bar(range(1, n_ev + 1), pct, color='steelblue', edgecolor='white', label='Per-PC %')
            ax1.set_xlabel('Principal Component')
            ax1.set_ylabel('Variance Explained (%)', color='steelblue')
            ax1.tick_params(axis='y', labelcolor='steelblue')
            ax1.set_xticks(range(1, n_ev + 1))

            ax2 = ax1.twinx()
            ax2.plot(range(1, n_ev + 1), cumulative, 'r-o', markersize=4, label='Cumulative %')
            ax2.set_ylabel('Cumulative Variance (%)', color='red')
            ax2.tick_params(axis='y', labelcolor='red')
            ax2.set_ylim(0, 105)

            ax1.set_title('Scree Plot')
            fname = os.path.join(out_dir, 'pca_scree.png')
            fig.savefig(fname, dpi=150, bbox_inches='tight')
            plt.close(fig)
            print(f'Saved {fname}')


if __name__ == '__main__':
    if len(sys.argv) != 4:
        print(f'Usage: {sys.argv[0]} <eigenfac.star> <motl_classified.star> <out_dir>')
        sys.exit(1)
    plot_pca_scatter(sys.argv[1], sys.argv[2], sys.argv[3])
