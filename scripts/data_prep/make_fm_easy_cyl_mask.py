#!/usr/bin/env python3
"""Build a CYLINDRICAL FM_easy mask (alternative to the diff sphere — less axial noise).
Cylinder axis = Y (the motor assembly axis / A-vs-C difference axis).
  radius = sphere R + 4 = 27 px (in the X-Z ring plane)
  full height = 0.5 * sphere diameter = 23 px (|y-cy| <= 11.5) along Y
  center = diff-sphere center (48, 55, 48); soft cosine edge 4 px (radial + axial)
Run with relion-5.0 env."""
import os, numpy as np, mrcfile
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt

OUT = "/home/jblaser2/Research/STA/packages/dynamo/dynamo_outputs/easy_pair_AC_hc"
ALN = "/home/jblaser2/Research/synthetic_sta/motor_easy/hc_test_x6/subtomos/merged_AC_full"
N = 96
# Cylinder spans y in [cy-HALF_H, cy+HALF_H]. Tweaked: top edge y=39.5, bottom edge y=63.5
# ("up the box" = decreasing Y; top moved up 4, bottom moved up 3 from the [43.5,66.5] version).
cx, cy, cz = 48.0, 51.5, 48.0          # center; y=51.5 = midpoint of [39.5, 63.5]
R = 27.0                                # = sphere R(23) + 4
HALF_H = 12.0                           # full height 24 (y in [39.5, 63.5])
EDGE = 4.0
APIX = 13.329

z, y, x = np.mgrid[0:N, 0:N, 0:N].astype(np.float32)
rad = np.sqrt((x - cx)**2 + (z - cz)**2)        # radial dist in X-Z plane (axis=Y)
ax = np.abs(y - cy)                              # axial dist along Y

def falloff(d, lim, edge):
    f = np.ones_like(d)
    e = (d > lim) & (d <= lim + edge)
    f[e] = 0.5 * (1 + np.cos(np.pi * (d[e] - lim) / edge))
    f[d > lim + edge] = 0.0
    return f

m = falloff(rad, R, EDGE) * falloff(ax, HALF_H, EDGE)
frac = 100 * float((m > 0.05).mean())
maskp = os.path.join(OUT, "diff_cyl_r27_h24_y52.mrc")
with mrcfile.new(maskp, overwrite=True) as o:
    o.set_data(m.astype(np.float32)); o.voxel_size = APIX
print(f"wrote {maskp}  radius={R:.0f} half_h={HALF_H} center=({cx:.0f},{cy:.0f},{cz:.0f})  active={frac:.1f}% of box")

# compare to sphere
sph = mrcfile.open(os.path.join(OUT, "diff_sphere_r23_y55.mrc"), permissive=True).data
print(f"  (diff sphere was {100*float((sph>0.05).mean()):.1f}% of box)")

# preview: cylinder vs sphere contour over class-A average
import csv
rows = list(csv.DictReader(open(os.path.join(ALN, "labels.csv"))))
acc = None; na = 0
for r in rows:
    if r["label"] != "A": continue
    v = mrcfile.open(os.path.join(ALN, r["file"]), permissive=True).data.astype(np.float32)
    acc = v if acc is None else acc + v; na += 1
A = acc / na
fig, axs = plt.subplots(1, 3, figsize=(11, 3.8))
views = [("XY (z=48)", A[48], m[48], sph[48]),
         ("XZ (y=52)", A[:, 52, :], m[:, 52, :], sph[:, 52, :]),
         ("YZ (x=48)", A[:, :, 48], m[:, :, 48], sph[:, :, 48])]
for a, (t, im, mk, sp) in zip(axs, views):
    lo, hi = np.percentile(im, [2, 98]); a.imshow(im, cmap="gray", vmin=lo, vmax=hi)
    a.contour(mk, levels=[0.5], colors="red", linewidths=1.8)
    a.contour(sp, levels=[0.5], colors="cyan", linewidths=1.0, linestyles="dashed")
    a.set_title(t, fontsize=10); a.axis("off")
fig.suptitle(f"FM_easy cylinder mask (red, r={R:.0f} h={2*HALF_H:.0f} y={cy:.0f}, {frac:.1f}%) vs diff sphere (cyan dashed) on class-A avg",
             fontsize=11, y=1.03)
plt.tight_layout(); pv = os.path.join(OUT, "diff_cyl_preview.png")
plt.savefig(pv, dpi=130, bbox_inches="tight"); plt.close(); print("saved", pv)
