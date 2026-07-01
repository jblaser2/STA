#!/usr/bin/env python3
"""Extract aligned particles from Dynamo dalign final table.

Reads:
  easy_AC_dalign/pair_labels.csv  — tag → (orig_file, gt_label)
  easy_AC_dalign/final_aligned.tbl — Dynamo refined table (40 cols)
    col 4-6: dx,dy,dz shifts (pixels, XYZ)
    col 7-9: tdrot,tilt,narot Euler angles (degrees, ZXZ)

Writes:
  ~/Research/synthetic_sta/motor_easy/hc_test_x6/subtomos/merged_AC_dalign/
    subtomo_XXXX.mrc  (aligned particles, same filenames as merged_AC_full)
    labels.csv

Prints blind masked-PCA ARI as sanity check (expect > 0.30 if alignment worked).

Run with relion-5.0 or eman2 env:
  conda run -n eman2 python3 packages/dynamo/FM_easy/scripts/extract_dalign_fm_easy.py
"""
import os, csv
import numpy as np
import mrcfile
from scipy.ndimage import affine_transform
from scipy.spatial.transform import Rotation
from math import comb

SRC     = os.path.expanduser("~/Research/synthetic_sta/motor_easy/hc_test_x6/subtomos/merged_AC_full")
DALIGN  = os.path.expanduser("~/Research/STA/packages/dynamo/dynamo_outputs/easy_AC_dalign")
OUT     = os.path.expanduser("~/Research/synthetic_sta/motor_easy/hc_test_x6/subtomos/merged_AC_dalign")
MASK    = os.path.join(DALIGN, "diff_sphere_r23_y55.mrc")
APIX    = 13.329
BOX     = 96

os.makedirs(OUT, exist_ok=True)

# Load labels (tag → orig_file, gt_label)
labels_file = os.path.join(DALIGN, "pair_labels.csv")
tag_to_info = {}
for row in csv.DictReader(open(labels_file)):
    tag_to_info[int(row["tag"])] = (row["orig_file"], row["gt_label"])

# Load final Dynamo table (space-delimited)
tbl_file = os.path.join(DALIGN, "final_aligned.tbl")
if not os.path.exists(tbl_file):
    raise FileNotFoundError(f"Final table not found: {tbl_file}\n"
                            "Run dalign_fm_easy.m first.")

table = {}
with open(tbl_file) as f:
    for line in f:
        vals = list(map(float, line.split()))
        tag = int(vals[0])
        # Dynamo table columns (1-indexed):
        # 4=dx, 5=dy, 6=dz (shifts in pixels, XYZ convention)
        # 7=tdrot (phi), 8=tilt (theta), 9=narot (psi) (ZXZ Euler angles, degrees)
        dx, dy, dz     = vals[3], vals[4], vals[5]
        phi, theta, psi = vals[6], vals[7], vals[8]
        table[tag] = (dx, dy, dz, phi, theta, psi)

print(f"Loaded table: {len(table)} entries")

# Load mask for sanity-check ARI
with mrcfile.open(MASK, permissive=True) as m:
    mask = m.data.astype(np.float32)
mb = mask > 0.05


def apply_dynamo_alignment(vol, phi, theta, psi, dx, dy, dz):
    """Apply Dynamo ZXZ alignment to bring particle into reference frame.

    Dynamo convention: (phi,theta,psi) describe how the reference was rotated
    to find the particle. To bring the particle to the reference: apply R^T.
    Shifts (dx,dy,dz) are the particle center offset from origin (XYZ pixels).

    vol: 3D float32 array (Z,Y,X numpy convention)
    """
    R = Rotation.from_euler("ZXZ", [phi, theta, psi], degrees=True).as_matrix()
    R_apply = R.T  # inverse rotation: bring particle to reference frame

    # Rotation around the volume center
    center = np.array(vol.shape, dtype=float) / 2.0 - 0.5

    # Shift in ZYX numpy order (Dynamo: dx=X, dy=Y, dz=Z)
    shift_zyx = np.array([dz, dy, dx])

    # affine_transform: out[o] = in[R_apply @ (o - offset)]
    # We want: bring the voxel at (center + shift) to center after rotation.
    # offset = center - R_apply @ (center + shift_zyx) maps center → aligned center
    offset = center - R_apply @ (center + shift_zyx)

    return affine_transform(vol, R_apply, offset=offset, order=1,
                            mode="constant", cval=0.0)


# Extract aligned particles
orig_vols = []
aligned_vols = []
out_rows = []

tags_sorted = sorted(tag_to_info.keys())
for tag in tags_sorted:
    orig_file, gt_label = tag_to_info[tag]
    src_path = os.path.join(SRC, orig_file)

    with mrcfile.open(src_path, permissive=True) as m:
        vol = m.data.astype(np.float32)

    dx, dy, dz, phi, theta, psi = table[tag]
    aligned = apply_dynamo_alignment(vol, phi, theta, psi, dx, dy, dz)

    # Write aligned particle (same filename as original)
    out_path = os.path.join(OUT, orig_file)
    with mrcfile.new(out_path, overwrite=True) as m:
        m.set_data(aligned.astype(np.float32))
        m.voxel_size = APIX

    orig_vols.append(vol)
    aligned_vols.append(aligned)
    out_rows.append({"file": orig_file, "label": gt_label})

    if tag % 50 == 0:
        print(f"  processed {tag}/{len(tags_sorted)}")

# Write labels.csv
labels_out = os.path.join(OUT, "labels.csv")
with open(labels_out, "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=["file", "label"])
    w.writeheader()
    w.writerows(out_rows)

print(f"\nWrote {len(out_rows)} aligned particles to: {OUT}")

# Sanity check: blind masked-PCA ARI on aligned set
print("\nRunning blind masked-PCA ARI sanity check...")
A = np.array(aligned_vols)
N = len(A)
y = np.array([0 if r["label"] == "A" else 1 for r in out_rows])

X = A.reshape(N, -1)[:, mb.ravel()]
X = X - X.mean(0)
_, S, Vt = np.linalg.svd(X, full_matrices=False)
Z = X @ Vt[:10].T  # top-10 PC scores


def ari(a, b):
    la = sorted(set(a)); lb = sorted(set(b))
    M = np.zeros((len(la), len(lb)), int)
    ia = {v: i for i, v in enumerate(la)}
    ib = {v: i for i, v in enumerate(lb)}
    for x, z in zip(a, b):
        M[ia[x], ib[z]] += 1
    sc = sum(comb(int(v), 2) for v in M.sum(0))
    sr = sum(comb(int(v), 2) for v in M.sum(1))
    si = sum(comb(int(v), 2) for v in M.flat)
    nn = comb(len(a), 2)
    e = sr * sc / nn
    mx = (sr + sc) / 2
    return (si - e) / (mx - e) if mx != e else 0.0


aris = []
rng = np.random.default_rng(0)
for seed in range(20):
    idx = rng.choice(N, 2, replace=False)
    cen = Z[idx].copy()
    for _ in range(200):
        d = ((Z[:, None, :] - cen[None]) ** 2).sum(-1).argmin(1)
        new_cen = np.array([Z[d == k].mean(0) if (d == k).any() else cen[k]
                            for k in range(2)])
        if np.allclose(new_cen, cen):
            break
        cen = new_cen
    aris.append(ari(y, d))

mean_ari = np.mean(aris)
std_ari = np.std(aris)
print(f"Blind masked-PCA ARI: {mean_ari:.3f} ± {std_ari:.3f}")
print(f"  (GT-pose baseline: 0.14; hand-rolled 4-iter: 0.26-0.32; target: >0.30)")
if mean_ari < 0.10:
    print("  WARNING: ARI suspiciously low — check Euler angle/shift sign convention")
elif mean_ari > 0.30:
    print("  GOOD: alignment improved classification signal")
else:
    print("  MARGINAL: some improvement over GT-pose baseline")
