import mrcfile, numpy as np, os
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
os.chdir(os.path.dirname(os.path.abspath(__file__)))
maps={1:'run_it025_class001.mrc',2:'run_it025_class002.mrc'}
fig,axs=plt.subplots(2,2,figsize=(8,8))
for col,(k,f) in enumerate(maps.items()):
    v=mrcfile.open(f,permissive=True).data.astype(np.float32); N=v.shape[0]; cz=N//2; cx=N//2
    axs[0,col].imshow(v[cz],cmap='gray'); axs[0,col].set_title(f"class{k:03d} — central Z",fontsize=11); axs[0,col].axis('off')
    axs[1,col].imshow(v[:,:,cx].T,cmap='gray'); axs[1,col].set_title(f"class{k:03d} — side (x={cx})",fontsize=11); axs[1,col].axis('off')
plt.suptitle("RELION k=2 A-vs-C class averages (focused diff mask)",fontsize=13)
plt.tight_layout(); p='class_avgs_relion_AC.png'; plt.savefig(p,dpi=140); print("saved",p)
