#!/bin/bash
# RELION Class3D on FM_hard (813 particles, 96^3, k=3, 3 assembly classes).
# Blind run: global-average init, no GT refs.
set -e
RELION=~/relion-install/bin/relion_refine
BASE=outputs/FM_hard/relion
STAR=$BASE/particles.star
REF=$BASE/initial_ref.mrc
MASK=$BASE/solvent_mask.mrc
GT_LABELS=~/Research/synthetic_sta/motor_hard/subtomos/merged_ABC_full/labels.csv
ITER="${ITER:-25}"
K=3

log() { echo "[$(date '+%H:%M:%S')] $*"; }

log "=== Step 1: Setup inputs ==="
conda run -n eman2 python3 packages/relion/FM_hard/scripts/setup_fm_hard_relion.py

OUT="$BASE/run_k${K}_blind"
mkdir -p "$OUT"
log "=== RELION Class3D FM_hard K=$K BLIND ==="
"$RELION" \
    --i "$STAR" --ref "$REF" --o "$OUT/run" \
    --K "$K" --iter "$ITER" --tau2_fudge 4 --ini_high 60 \
    --solvent_mask "$MASK" --flatten_solvent --zero_mask \
    --skip_align \
    --sym C1 --ctf --skip_subtomo_multi --pad 2 --random_seed 1 \
    --dont_combine_weights_via_disc --j 8 --gpu "" \
    > "$OUT/run.log" 2>&1
log "K=$K done -> $OUT"

LAST=$(ls "$OUT"/run_it*_data.star 2>/dev/null | sort | tail -1)
[ -n "$LAST" ] || { log "ERROR: no data.star"; exit 1; }
log "Parsing $LAST"

conda run -n eman2 python3 - "$LAST" "$OUT/pred_k${K}.csv" "$GT_LABELS" "$K" <<'PYEOF'
import sys, os, csv
from sklearn.metrics import adjusted_rand_score
from collections import Counter

star_path, pred_csv, gt_csv, K = sys.argv[1], sys.argv[2], sys.argv[3], int(sys.argv[4])
block = None; cols = {}; data = []
for line in open(star_path):
    s = line.strip()
    if s.startswith("data_"): block = s; cols = {}; continue
    if block == "data_particles":
        if s.startswith("_rln"): cols[s.split()[0]] = len(cols)
        elif s and not s.startswith(("loop","#")) and cols and len(s.split()) >= len(cols):
            data.append(s.split())

ii = cols["_rlnImageName"]; ci = cols["_rlnClassNumber"]
gt_rows = list(csv.DictReader(open(gt_csv)))
gt_map  = {r['file']: r['label'] for r in gt_rows}
pred_map = {os.path.basename(r[ii]): int(r[ci]) for r in data}

os.makedirs(os.path.dirname(os.path.abspath(pred_csv)), exist_ok=True)
with open(pred_csv, 'w', newline='') as f:
    w = csv.writer(f); w.writerow(['file','pred_label'])
    for row in gt_rows: w.writerow([row['file'], pred_map.get(row['file'],0)])

files = [r['file'] for r in gt_rows]
gt_list = [gt_map[f] for f in files]
pr_list = [pred_map.get(f,0) for f in files]
ari = adjusted_rand_score(gt_list, pr_list)
print(f"RELION FM_hard k={K}: ARI={ari:.3f}  classes={dict(sorted(Counter(pr_list).items()))}")
PYEOF

log "=== RELION FM_hard complete ==="
