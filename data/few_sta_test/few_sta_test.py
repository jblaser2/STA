#!/usr/bin/env python3
"""
Experiment: Does duplicating a small particle set improve FSC resolution?

Two conditions:
  A) Duplicated — take 25 particles, multiply them 1x / 2x / 4x / 8x / 16x
  B) Real unique — use 25 / 50 / 100 / 200 / 400 genuinely different particles

For each condition and N we compute the split-half FSC and read off the
resolution at FSC=0.5.  The key result: duplication inflates the FSC because
both halves contain the same noise pattern, so apparent resolution improves
artifactually.  Real particles have independent noise and the FSC is honest.

Outputs saved to the script directory:
  avg_dup_N????.mrc        average volumes — duplicated
  avg_real_N????.mrc       average volumes — real unique
  fsc_comparison.png       FSC curves, both conditions
  resolution_vs_N.png      resolution vs N summary

Usage:
  DISPLAY=:0 QT_QPA_PLATFORM=xcb \\
      /home/jblaser2/conda-envs/napari-0.4-env/bin/python3 few_sta_test.py
"""

import os
import sys
import numpy as np
import mrcfile
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

SCRIPT_DIR   = os.path.dirname(os.path.abspath(__file__))
SUBTOMOS_DIR = '/home/jblaser2/Research/STA/subtomos_mrc'
PIXEL_ANG    = 13.328
N_BASE       = 25
MULTIPLIERS  = [1, 2, 4, 8, 16]   # N = 25, 50, 100, 200, 400
REAL_NS      = [25, 50, 100, 200, 400]
SEED         = 42

# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

def load_vol(path):
    with mrcfile.open(path, permissive=True) as f:
        return f.data.copy().astype(np.float32)

def save_mrc(vol, path):
    with mrcfile.new(path, overwrite=True) as f:
        f.set_data(vol.astype(np.float32))
        f.voxel_size = PIXEL_ANG

def compute_fsc(vol1, vol2, n_shells=40):
    """Split-half FSC via FFT shells."""
    box = vol1.shape[0]
    F1 = np.fft.fftn(vol1 - vol1.mean())
    F2 = np.fft.fftn(vol2 - vol2.mean())

    # radial coordinate in pixel units (DC at index 0)
    k1d = np.fft.fftfreq(box) * box
    kz, ky, kx = np.meshgrid(k1d, k1d, k1d, indexing='ij')
    r = np.sqrt(kx**2 + ky**2 + kz**2)

    max_r = box // 2
    edges = np.linspace(0, max_r, n_shells + 1)
    fsc   = np.zeros(n_shells)
    freq  = np.zeros(n_shells)

    for i in range(n_shells):
        mask = (r >= edges[i]) & (r < edges[i + 1])
        if mask.sum() < 3:
            continue
        f1, f2 = F1[mask], F2[mask]
        num   = np.real(np.sum(f1 * np.conj(f2)))
        denom = np.sqrt(np.sum(np.abs(f1) ** 2) * np.sum(np.abs(f2) ** 2))
        fsc[i]  = num / denom if denom > 0 else 0.0
        freq[i] = (edges[i] + edges[i + 1]) / 2 / box   # 1/pixel

    return freq, fsc

def resolution_at(freq, fsc, threshold=0.5):
    """Angstrom resolution at given FSC threshold (linear interpolation)."""
    for i in range(len(fsc) - 1):
        if fsc[i] >= threshold > fsc[i + 1] and freq[i + 1] > 0:
            t = (threshold - fsc[i]) / (fsc[i + 1] - fsc[i])
            f_cross = freq[i] + t * (freq[i + 1] - freq[i])
            return PIXEL_ANG / f_cross if f_cross > 0 else np.inf
    return np.inf

def run_condition(vol_list, tag, split_seed=0):
    """Average vols and compute split-half FSC. Returns (avg, freq, fsc, res_ang)."""
    arr = np.stack(vol_list)          # (N, box, box, box)
    N   = len(arr)
    rng = np.random.default_rng(SEED + split_seed)
    perm = rng.permutation(N)
    h1, h2 = perm[: N // 2], perm[N // 2 :]
    avg1 = arr[h1].mean(axis=0)
    avg2 = arr[h2].mean(axis=0)
    avg  = arr.mean(axis=0)
    freq, fsc = compute_fsc(avg1, avg2)
    res = resolution_at(freq, fsc)
    res_str = f'{res:.1f} Å' if np.isfinite(res) else 'never crosses FSC=0.5'
    print(f'  {tag:<30}  N={N:>4}  res={res_str}')
    return avg, freq, fsc, res

# ------------------------------------------------------------------
# Load particles
# ------------------------------------------------------------------
all_files = sorted(f for f in os.listdir(SUBTOMOS_DIR) if f.endswith('.mrc'))
N_total   = len(all_files)
print(f'Found {N_total} particles in {SUBTOMOS_DIR}')

rng_main = np.random.default_rng(SEED)
base_idx  = rng_main.choice(N_total, N_BASE, replace=False)
real_idx  = rng_main.choice(N_total, max(REAL_NS), replace=False)

print(f'Loading {N_BASE} base particles...')
base_vols = [load_vol(os.path.join(SUBTOMOS_DIR, all_files[i])) for i in base_idx]
box = base_vols[0].shape[0]
print(f'  box = {box}^3  pixel = {PIXEL_ANG} Å/vox')

print(f'Loading {max(REAL_NS)} real unique particles...')
real_vols = [load_vol(os.path.join(SUBTOMOS_DIR, all_files[i])) for i in real_idx]

# ------------------------------------------------------------------
# Run experiments
# ------------------------------------------------------------------
print('\n=== Condition A: duplicated augmentation ===')
dup_results = {}
for mult in MULTIPLIERS:
    vols = base_vols * mult   # Python list duplication — identical arrays
    avg, freq, fsc, res = run_condition(vols, f'dup {N_BASE}x{mult}', split_seed=mult)
    dup_results[mult] = {'avg': avg, 'freq': freq, 'fsc': fsc, 'res': res,
                         'N': N_BASE * mult}
    fname = os.path.join(SCRIPT_DIR, f'avg_dup_N{N_BASE * mult:04d}.mrc')
    save_mrc(avg, fname)

print('\n=== Condition B: real unique particles ===')
real_results = {}
for n in REAL_NS:
    avg, freq, fsc, res = run_condition(real_vols[:n], f'real {n}', split_seed=n)
    real_results[n] = {'avg': avg, 'freq': freq, 'fsc': fsc, 'res': res, 'N': n}
    fname = os.path.join(SCRIPT_DIR, f'avg_real_N{n:04d}.mrc')
    save_mrc(avg, fname)

# ------------------------------------------------------------------
# FSC comparison plot
# ------------------------------------------------------------------
fig, axes = plt.subplots(1, 2, figsize=(14, 5))
cmap_blue = plt.cm.Blues(np.linspace(0.35, 1.0, len(MULTIPLIERS)))
cmap_red  = plt.cm.Reds(np.linspace(0.35, 1.0, len(REAL_NS)))

for ax, results, ns, cmap, title in [
    (axes[0], dup_results,  MULTIPLIERS, cmap_blue,
     f'A) Duplicated augmentation\n(same {N_BASE} particles, multiplied)'),
    (axes[1], real_results, REAL_NS,     cmap_red,
     'B) Real unique particles\n(genuinely independent subvolumes)'),
]:
    for i, n in enumerate(ns):
        r = results[n]
        res_str = f'{r["res"]:.0f} Å' if np.isfinite(r["res"]) else '—'
        ax.plot(r['freq'], r['fsc'], color=cmap[i], linewidth=2,
                label=f'N={r["N"]:>4}  res={res_str}')
    ax.axhline(0.5,   color='gray',      linestyle='--', linewidth=1, label='FSC=0.5')
    ax.axhline(0.143, color='lightgray', linestyle=':',  linewidth=1, label='FSC=0.143')
    ax.set_xlim(0, 0.5)
    ax.set_ylim(-0.1, 1.05)
    ax.set_xlabel('Spatial frequency (1/vox)', fontsize=10)
    ax.set_ylabel('FSC', fontsize=10)
    ax.set_title(title, fontsize=11)
    ax.legend(fontsize=8, loc='upper right')
    ax.grid(True, alpha=0.3)

fig.suptitle(
    f'Does data duplication improve FSC resolution?\n'
    f'Pixel: {PIXEL_ANG} Å/vox  |  Box: {box}³  |  Base set: {N_BASE} particles',
    fontsize=12
)
fig.tight_layout()
png_fsc = os.path.join(SCRIPT_DIR, 'fsc_comparison.png')
fig.savefig(png_fsc, dpi=150, bbox_inches='tight')
plt.close(fig)
print(f'\nSaved: {png_fsc}')

# Resolution vs N summary plot
fig, ax = plt.subplots(figsize=(7, 5))
dup_n_arr  = [dup_results[m]['N']  for m in MULTIPLIERS]
dup_r_arr  = [dup_results[m]['res'] if np.isfinite(dup_results[m]['res']) else np.nan
              for m in MULTIPLIERS]
real_n_arr = [real_results[n]['N']  for n in REAL_NS]
real_r_arr = [real_results[n]['res'] if np.isfinite(real_results[n]['res']) else np.nan
              for n in REAL_NS]

ax.plot(dup_n_arr,  dup_r_arr,  'b-o', linewidth=2, markersize=8,
        label='A) Duplicated (same 25 particles)')
ax.plot(real_n_arr, real_r_arr, 'r-o', linewidth=2, markersize=8,
        label='B) Real unique particles')
ax.set_xlabel('N particles averaged', fontsize=11)
ax.set_ylabel('Resolution at FSC=0.5 (Å)', fontsize=11)
ax.set_title('Resolution vs N: duplication vs real data', fontsize=12)
ax.invert_yaxis()
ax.legend(fontsize=10)
ax.grid(True, alpha=0.3)
fig.tight_layout()
res_png = os.path.join(SCRIPT_DIR, 'resolution_vs_N.png')
fig.savefig(res_png, dpi=150, bbox_inches='tight')
plt.close(fig)
print(f'Saved: {res_png}')

# ------------------------------------------------------------------
# Print summary table
# ------------------------------------------------------------------
print('\n' + '=' * 60)
print(f'{"Method":<34} {"N":>5}  {"Res FSC=0.5":>12}')
print('=' * 60)
for mult in MULTIPLIERS:
    r = dup_results[mult]
    res_str = f'{r["res"]:.1f} Å' if np.isfinite(r['res']) else 'N/A'
    print(f'  Dup  {N_BASE}×{mult:<3} ("augmented")     {r["N"]:>5}  {res_str:>12}')
print('-' * 60)
for n in REAL_NS:
    r = real_results[n]
    res_str = f'{r["res"]:.1f} Å' if np.isfinite(r['res']) else 'N/A'
    print(f'  Real unique                    {r["N"]:>5}  {res_str:>12}')
print('=' * 60)
print(f'\nAll files saved to: {SCRIPT_DIR}')

# ------------------------------------------------------------------
# Open napari
# ------------------------------------------------------------------
print('\nOpening napari...')
import napari

viewer = napari.Viewer(
    title=f'STA augmentation experiment — {N_BASE} base particles',
    ndisplay=2
)

z_mid = box // 2

# Row 0: duplicated averages; row 1: real averages
dup_avgs  = [dup_results[m]['avg']  for m in MULTIPLIERS]
real_avgs = [real_results[n]['avg'] for n in REAL_NS]

col_gap = box * PIXEL_ANG * 1.15
row_gap = box * PIXEL_ANG * 1.3

for col, mult in enumerate(MULTIPLIERS):
    vol = dup_results[mult]['avg']
    n   = dup_results[mult]['N']
    res = dup_results[mult]['res']
    res_str = f'{res:.0f}Å' if np.isfinite(res) else 'N/A'
    viewer.add_image(
        vol,
        name=f'A) dup N={n} ({mult}×)  res={res_str}',
        colormap='gray',
        contrast_limits=[np.percentile(vol, 1), np.percentile(vol, 99)],
        scale=[PIXEL_ANG] * 3,
        translate=[0, 0, col * col_gap],
    )

for col, n in enumerate(REAL_NS):
    vol = real_results[n]['avg']
    res = real_results[n]['res']
    res_str = f'{res:.0f}Å' if np.isfinite(res) else 'N/A'
    viewer.add_image(
        vol,
        name=f'B) real N={n}  res={res_str}',
        colormap='magenta',
        contrast_limits=[np.percentile(vol, 1), np.percentile(vol, 99)],
        scale=[PIXEL_ANG] * 3,
        translate=[row_gap, 0, col * col_gap],
        blending='translucent_no_depth',
    )

# Load FSC comparison PNG as a 2D image layer
fsc_img = plt.imread(png_fsc)
viewer.add_image(
    fsc_img,
    name='FSC comparison (plot)',
    scale=[1, 1],
    translate=[2 * row_gap, 0],
    colormap='gray',
    rgb=True,
)

viewer.dims.current_step = (z_mid, 0, 0)
viewer.dims.axis_labels  = ('Z', 'Y', 'X')

print('Controls:')
print('  Gray  (row 0)    = duplicated averages')
print('  Magenta (row 1)  = real unique particle averages')
print('  Scroll Z to move through slices')
print('  Toggle layers in the panel to compare')

napari.run()
