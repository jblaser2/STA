import os
import numpy as np
import napari

here = os.path.dirname(os.path.abspath(__file__))

avg  = np.load(os.path.join(here, 'starting_average.npy'))
mask = np.load(os.path.join(here, 'cylindrical_mask.npy'))

viewer = napari.Viewer(title='T4P Global Average vs Cylindrical Mask')
viewer.add_image(avg,  name='global_average',    colormap='gray',  contrast_limits=[avg.min(), avg.max()])
viewer.add_image(mask, name='cylindrical_mask',  colormap='green', opacity=0.4, blending='additive')

print("Use the slice slider to step through Z slices.")
print("Toggle layer visibility with the eye icon on each layer.")
napari.run()
