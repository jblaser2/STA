#!/usr/bin/env python3
"""Extract OPUS-TOMO k-means class assignments from analyze.{epoch}/kmeans{K}/labels.pkl
into a standardized results CSV.

Usage:
    python extract_opus_tomo_classes.py --epoch 19 --k 2 --out results/opus_tomo_k2.csv
    python extract_opus_tomo_classes.py --last-epoch --k 8 --out results/opus_tomo_k8.csv
"""
import argparse, csv, os, pickle, glob, numpy as np
from collections import Counter

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OPUS_SCRIPTS = os.path.join(SCRIPT_DIR, '../../opusTomo/scripts')


def find_last_epoch(outdir):
    pkls = glob.glob(os.path.join(outdir, 'z.*.pkl'))
    epochs = [int(os.path.basename(p).replace('z.', '').replace('.pkl', '')) for p in pkls]
    return max(epochs) if epochs else None


def load_star_filenames(star_path):
    files = []
    with open(star_path) as f:
        for line in f:
            s = line.strip()
            if s and not s.startswith(('#', 'data', 'loop', '_')):
                parts = s.split()
                if parts:
                    files.append(parts[0])
    return files


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--epoch', type=int, default=None, help='Epoch number (default: last)')
    ap.add_argument('--last-epoch', action='store_true')
    ap.add_argument('--k', type=int, default=2, help='Number of clusters')
    ap.add_argument('--out', required=True, help='Output CSV path')
    ap.add_argument('--scripts-dir', default=OPUS_SCRIPTS,
                    help=f'Path to opusTomo/scripts/ (default: {OPUS_SCRIPTS})')
    args = ap.parse_args()

    outdir = os.path.join(args.scripts_dir, 'output')
    star = os.path.join(args.scripts_dir, 'particles.star')

    epoch = args.epoch
    if args.last_epoch or epoch is None:
        epoch = find_last_epoch(outdir)
        if epoch is None:
            raise FileNotFoundError(f'No z.*.pkl found in {outdir}')
        print(f'Using last epoch: {epoch}')

    labels_path = os.path.join(outdir, f'analyze.{epoch}', f'kmeans{args.k}', 'labels.pkl')
    if not os.path.exists(labels_path):
        raise FileNotFoundError(f'{labels_path} not found — run analysis first')

    labels = pickle.load(open(labels_path, 'rb'))
    files = load_star_filenames(star)

    if len(files) != len(labels):
        raise ValueError(f'Mismatch: {len(files)} particles vs {len(labels)} labels')

    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    with open(args.out, 'w', newline='') as f:
        w = csv.writer(f)
        w.writerow(['file', 'pred_label'])
        for fn, lb in zip(files, labels):
            w.writerow([fn, int(lb)])

    print(f'K={args.k} distribution: {dict(sorted(Counter(int(l) for l in labels).items()))}')
    print(f'Saved {len(labels)} rows -> {args.out}')


if __name__ == '__main__':
    main()
