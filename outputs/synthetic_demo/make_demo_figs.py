"""
make_demo_figs.py — Synthetic STA pipeline demo figures for Stefano
Run: cd ~/Research/STA/outputs/synthetic_demo && conda run -n pytom_env python make_demo_figs.py
Outputs: figures/  (PNG + GIF, committable to GitHub — no .mrc files)

Pipeline shown:
  Original class maps (A/B/C) → nonoise tomogram → raw subvolumes (GIF) →
  aligned subvolumes (PNG) → average (PNG)
  … repeated for noisy tomogram
"""
import os
from pathlib import Path

import numpy as np
import mrcfile
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from scipy.ndimage import gaussian_filter
from PIL import Image

# ── paths ───────────────────────────────────────────────────────────────────
BASE = Path("/home/jblaser2/Research/synthetic_sta/motor_easy")
OUT  = Path("figures")
OUT.mkdir(exist_ok=True)

BOX  = 96
HALF = BOX // 2

# ── helpers ──────────────────────────────────────────────────────────────────
def read_mrc(path):
    with mrcfile.mmap(path, mode='r', permissive=True) as m:
        return m.data.astype('float32')

def norm(arr, lo_pct=1, hi_pct=99):
    lo, hi = np.percentile(arr, lo_pct), np.percentile(arr, hi_pct)
    return np.clip((arr - lo) / (hi - lo + 1e-9), 0, 1)

def save_png(arr2d, path, title=None, dpi=150):
    fig, ax = plt.subplots(figsize=(4, 4))
    ax.imshow(arr2d, cmap='gray', origin='lower', vmin=0, vmax=1)
    if title:
        ax.set_title(title, fontsize=9)
    ax.axis('off')
    fig.savefig(path, dpi=dpi, bbox_inches='tight', pad_inches=0.05)
    plt.close(fig)
    print(f"  {Path(path).name}")

def save_gif(vol3d, path, n=30, fps=6, size=192):
    mid = vol3d.shape[0] // 2
    z0  = max(0, mid - n // 2)
    z1  = min(vol3d.shape[0], z0 + n)
    v   = norm(vol3d)
    frames = []
    for z in range(z0, z1):
        sl = (v[z] * 255).astype(np.uint8)
        frames.append(Image.fromarray(sl).resize((size, size), Image.NEAREST))
    frames[0].save(path, save_all=True, append_images=frames[1:],
                   loop=0, duration=int(1000 / fps))
    print(f"  {Path(path).name}")

def load_coords(coord_txt):
    """coord.txt: first line is 'N 6', remaining lines are x y z euler1 euler2 euler3 in voxels."""
    with open(coord_txt) as f:
        f.readline()
        rows = [list(map(float, l.split()))[:3] for l in f if l.strip()]
    return np.array(rows)

def extract_box(tomo, xc, yc, zc):
    nz, ny, nx = tomo.shape
    h = HALF
    if not (h <= xc < nx-h and h <= yc < ny-h and h <= zc < nz-h):
        return None
    b = tomo[zc-h:zc+h, yc-h:yc+h, xc-h:xc+h].copy()
    return (b - b.mean()) / (b.std() + 1e-9)

def cc_align_all(boxes, n_iter=2):
    """Iterative translational CC alignment; returns list of aligned boxes."""
    aligned = list(boxes)
    for _ in range(n_iter):
        ref = gaussian_filter(np.mean(aligned, axis=0), 2.5)
        Rf  = np.conj(np.fft.fftn(ref))
        new = []
        for b in boxes:
            cc = np.real(np.fft.ifftn(np.fft.fftn(gaussian_filter(b, 2.5)) * Rf))
            p  = np.unravel_index(np.argmax(cc), cc.shape)
            sh = np.array([(q if q <= BOX//2 else q - BOX) for q in p])
            new.append(np.roll(b, (-sh).astype(int), axis=(0, 1, 2)))
        aligned = new
    return aligned

def extract_all(tomo, coords):
    boxes = []
    nz, ny, nx = tomo.shape
    for xp, yp, zp in coords:
        xc = int(round(xp + nx / 2))
        yc = int(round(yp + ny / 2))
        zc = int(round(zp + nz / 2))
        b  = extract_box(tomo, xc, yc, zc)
        if b is not None:
            boxes.append(b)
    return boxes

# ── 1. Class maps ────────────────────────────────────────────────────────────
print("Class maps:")
for cls, fname in [('A', 'class_A_full.mrc'),
                   ('B', 'class_B_noCring.mrc'),
                   ('C', 'class_C_core.mrc')]:
    vol = read_mrc(BASE / 'maps' / fname)
    mid = vol.shape[0] // 2
    save_png(norm(vol[mid]), OUT / f'class_{cls}_map.png',
             title=f'Class {cls} — original density map')

# ── 2–5. Nonoise pipeline ─────────────────────────────────────────────────────
print("Nonoise tomogram:")
tomo_nn = read_mrc(BASE / 'run_A' / 'MotorA_nonoise_rec_rotx.mrc')
nz, ny, nx = tomo_nn.shape
coords = load_coords(BASE / 'run_A' / 'coord.txt')

# 2. Tomogram central slice (2000×2000 → downsampled ×4 for display)
mid_z = nz // 2
step  = 4
save_png(norm(tomo_nn[mid_z, ::step, ::step]),
         OUT / 'tomo_nonoise_central.png',
         title=f'Nonoise tomogram central Z (120 class A particles, {nx}×{ny} px)')

# 3. Extract all; GIFs for first 3
print("Extracting nonoise particles...")
boxes_nn = extract_all(tomo_nn, coords)
print(f"  {len(boxes_nn)} particles")
for i in range(3):
    save_gif(boxes_nn[i], OUT / f'nonoise_raw_p{i}.gif')

# 4. CC-align; PNG central slices for first 3
print("Aligning nonoise...")
aligned_nn = cc_align_all(boxes_nn)
for i in range(3):
    mid = aligned_nn[i].shape[0] // 2
    save_png(norm(aligned_nn[i][mid]), OUT / f'nonoise_aln_p{i}.png',
             title=f'Nonoise particle {i} — aligned (central slice)')

# 5. Average
avg_nn = np.mean(aligned_nn, axis=0)
mid = avg_nn.shape[0] // 2
save_png(norm(avg_nn[mid]), OUT / 'nonoise_avg.png',
         title=f'Nonoise class A average  N={len(aligned_nn)}')

del tomo_nn, boxes_nn, aligned_nn

# ── 6–9. Noisy pipeline ───────────────────────────────────────────────────────
print("Noisy tomogram:")
tomo_ns = read_mrc(BASE / 'run_A' / 'MotorA_0_rec_rotx.mrc')

# 6. Tomogram central slice
save_png(norm(tomo_ns[mid_z, ::step, ::step]),
         OUT / 'tomo_noise_central.png',
         title=f'Noisy tomogram central Z (120 class A particles)')

# 7. Extract all; GIFs for first 3
print("Extracting noisy particles...")
boxes_ns = extract_all(tomo_ns, coords)
print(f"  {len(boxes_ns)} particles")
for i in range(3):
    save_gif(boxes_ns[i], OUT / f'noise_raw_p{i}.gif')

# 8. CC-align; PNG central slices for first 3
print("Aligning noisy...")
aligned_ns = cc_align_all(boxes_ns)
for i in range(3):
    mid = aligned_ns[i].shape[0] // 2
    save_png(norm(aligned_ns[i][mid]), OUT / f'noise_aln_p{i}.png',
             title=f'Noisy particle {i} — aligned (central slice)')

# 9. Average
avg_ns = np.mean(aligned_ns, axis=0)
mid = avg_ns.shape[0] // 2
save_png(norm(avg_ns[mid]), OUT / 'noise_avg.png',
         title=f'Noisy class A average  N={len(aligned_ns)}')

print(f"\nDone — {len(list(OUT.iterdir()))} files in {OUT}/")
