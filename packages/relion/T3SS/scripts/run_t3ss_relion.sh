#!/bin/bash
# RELION Class3D on T3SS injectisome (415 particles, 48^3).
# Junk protocol: K=2 (blind B vs C, junk=noise) and K=3 (junk should isolate).
# Blind run: global-average init, no GT refs — same fair footing as other packages.
# Run from STA repo root.
set -e

RELION=~/relion-install/bin/relion_refine
BASE=outputs/T3SS/relion
STAR=$BASE/particles_wedge.star
REF=$BASE/initial_ref.mrc
MASK=$BASE/solvent_mask.mrc
GT_LABELS=~/Research/synthetic_sta/injectisome/subtomos/merged_BC_t3ss/labels.csv
ITER="${ITER:-25}"

log() { echo "[$(date '+%H:%M:%S')] $*"; }

for K in 2 3; do
    OUT="$BASE/run_k${K}_blind"
    mkdir -p "$OUT"
    log "=== RELION Class3D T3SS K=$K BLIND ==="
    "$RELION" \
        --i "$STAR" --ref "$REF" --o "$OUT/run" \
        --K "$K" --iter "$ITER" --tau2_fudge 4 --ini_high 60 \
        --solvent_mask "$MASK" --flatten_solvent --zero_mask \
        --skip_align \
        --sym C1 --ctf --skip_subtomo_multi --pad 2 --random_seed 1 \
        --dont_combine_weights_via_disc --j 8 --gpu "" \
        > "$OUT/run.log" 2>&1
    log "K=$K done -> $OUT"

    # Extract predictions from last iteration
    LAST=$(ls "$OUT"/run_it*_data.star 2>/dev/null | sort | tail -1)
    [ -n "$LAST" ] || { log "ERROR: no data.star found in $OUT"; continue; }
    log "Parsing $LAST"

    conda run -n eman2 python3 - "$LAST" "$OUT/pred_k${K}.csv" "$GT_LABELS" "$K" <<'PYEOF'
import sys, os, csv
from sklearn.metrics import adjusted_rand_score
from collections import Counter

star_path, pred_csv, gt_csv, K = sys.argv[1], sys.argv[2], sys.argv[3], int(sys.argv[4])

# Parse STAR file for ImageName and ClassNumber
block = None; cols = {}; data = []
for line in open(star_path):
    s = line.strip()
    if s.startswith("data_"): block = s; cols = {}; continue
    if block == "data_particles":
        if s.startswith("_rln"): cols[s.split()[0]] = len(cols)
        elif s and not s.startswith(("loop","#")) and cols and len(s.split()) >= len(cols):
            data.append(s.split())

ii = cols["_rlnImageName"]; ci = cols["_rlnClassNumber"]

# GT labels
gt_rows = list(csv.DictReader(open(gt_csv)))
gt_map  = {r['file']: r['label'] for r in gt_rows}

# Build pred map: file -> class
pred_map = {}
for r in data:
    fname = os.path.basename(r[ii])
    pred_map[fname] = int(r[ci])

# Save CSV
with open(pred_csv, 'w', newline='') as f:
    w = csv.writer(f); w.writerow(['file','pred_label'])
    for row in gt_rows:
        w.writerow([row['file'], pred_map.get(row['file'], 0)])

# Score B vs C only
signal = [r for r in gt_rows if gt_map[r['file']] in ('class_B','class_C')]
gt_sig = [gt_map[r['file']] for r in signal]
pr_sig = [pred_map.get(r['file'], 0) for r in signal]

ari = adjusted_rand_score(gt_sig, pr_sig)
all_cls = [pred_map.get(r['file'],0) for r in gt_rows]
print(f"RELION T3SS k={K}: ARI(B/C)={ari:.3f}  classes={dict(sorted(Counter(all_cls).items()))}")
print(f"  pred CSV -> {pred_csv}")
PYEOF

done

log "=== All RELION T3SS runs complete ==="
