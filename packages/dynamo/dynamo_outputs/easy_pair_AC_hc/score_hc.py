import csv, os, numpy as np
from collections import Counter
from math import comb
from scipy.optimize import linear_sum_assignment
os.chdir(os.path.dirname(os.path.abspath(__file__)))
lab={int(r['tag']):r['gt_label'] for r in csv.DictReader(open('pair_labels.csv'))}
pred={int(r['tag']):int(r['pred_label']) for r in csv.DictReader(open('predictions_k2.csv'))}
tags=sorted(lab); y=[lab[t] for t in tags]; p=[pred[t] for t in tags]
la=sorted(set(y)); lb=sorted(set(p)); M=np.zeros((len(la),len(lb)),int)
ia={v:i for i,v in enumerate(la)}; ib={v:i for i,v in enumerate(lb)}
for a,b in zip(y,p): M[ia[a],ib[b]]+=1
sc=sum(comb(int(v),2) for v in M.sum(0)); sr=sum(comb(int(v),2) for v in M.sum(1))
si=sum(comb(int(v),2) for v in M.flat); n=comb(len(y),2); e=sr*sc/n; mx=(sr+sc)/2
ari=(si-e)/(mx-e) if mx!=e else 0.0
ri,ci=linear_sum_assignment(-M); acc=M[ri,ci].sum()/len(y)
print("N=",len(y),"GT:",dict(Counter(y)),"pred:",dict(Counter(p)))
print("confusion rows=GT",la,"cols=cluster",lb,"\n",M)
print(f"Dynamo dpkpca HIGH-CONTRAST: ARI={ari:.3f}  acc={acc:.3f}")
print("(production SNR0.21 Dynamo=0.003; blind-PCA hc 20-seed=0.151; supervised ceiling=0.80)")
