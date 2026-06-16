import csv,os,numpy as np
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
os.chdir(os.path.dirname(os.path.abspath(__file__)))
lab={int(r['tag']):r['gt_label'] for r in csv.DictReader(open('pair_labels.csv'))}
pred={int(r['tag']):int(r['pred_label']) for r in csv.DictReader(open('predictions_k2.csv'))}
tags=sorted(lab); y=[lab[t] for t in tags]; p=[pred[t] for t in tags]
la=['A','C']; lb=sorted(set(p)); M=np.zeros((2,len(lb)),int)
for a,b in zip(y,p): M[la.index(a),lb.index(b)]+=1
fig,ax=plt.subplots(figsize=(4.6,4))
ax.imshow(M,cmap='Purples'); ax.set_xticks(range(len(lb))); ax.set_yticks([0,1])
ax.set_xticklabels([f'cluster{c}' for c in lb]); ax.set_yticklabels(['GT A','GT C'])
for i in range(2):
    for j in range(len(lb)): ax.text(j,i,M[i,j],ha='center',va='center',fontsize=15,fontweight='bold',color='white' if M[i,j]>M.max()/2 else 'black')
ax.set_title('Dynamo dpkpca k=2 — HIGH CONTRAST (SNR 0.36)\nARI=0.280 acc=0.77 (production SNR0.21 was 0.003)')
plt.tight_layout(); plt.savefig('confusion_dynamo_hc.png',dpi=140); print('saved')
