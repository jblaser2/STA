"""Convert cylindrical_mask.npy → valid .em files using PyTom's own vol.write()."""
import numpy as np
from pytom.lib.pytom_volume import vol

TARGETS = [
    ('/home/jblaser2/Research/STA/PyTom/cylindrical_mask.npy',
     '/home/jblaser2/Research/STA/PyTom/cylindrical_mask.em'),
    ('/home/jblaser2/Research/STA/T4P_mask/cylindrical_mask.npy',
     '/home/jblaser2/Research/STA/T4P_mask/cylindrical_mask.em'),
]

for npy_path, em_path in TARGETS:
    mask = np.load(npy_path).astype(np.float32)  # shape (nz, ny, nx)
    nz, ny, nx = mask.shape
    v = vol(nx, ny, nz)
    for iz in range(nz):
        for iy in range(ny):
            for ix in range(nx):
                v.setV(float(mask[iz, iy, ix]), ix, iy, iz)
    v.write(em_path)
    print(f"Wrote {em_path}  (nonzero: {int(mask.sum())})")
