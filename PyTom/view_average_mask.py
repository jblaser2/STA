import numpy as np
import napari

avg = np.load('/home/jblaser2/Research/STA/PyTom/starting_average.npy')
mask = np.load('/home/jblaser2/Research/STA/PyTom/cylindrical_mask.npy')

viewer = napari.Viewer(title='Average vs Cylindrical Mask')
viewer.add_image(avg, name='global_average', colormap='gray', contrast_limits=[avg.min(), avg.max()])
viewer.add_image(mask, name='cylindrical_mask', colormap='green', opacity=0.4, blending='additive')

print("Napari open. Use the slice slider to inspect overlap between the average and the mask.")
print("Toggle layer visibility with the eye icon on each layer.")
napari.run()
