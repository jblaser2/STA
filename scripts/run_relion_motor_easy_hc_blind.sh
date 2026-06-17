#!/bin/bash
# RELION Class3D BLIND on the 2-class hc FM_easy (542 A/C), K=2 — FAIR (no GT refs).
# Single global-average reference; RELION splits via stochastic E-step (random seed).
# No --firstiter_cc, no per-class GT seeding: matches the unsupervised footing of the
# other packages. (Documented historical blind RELION collapses to ARI≈0 on this data.)
set -e
RELION=/home/jblaser2/relion-install/bin/relion_refine
BASE=outputs/FM_easy/relion
REF=$BASE/initial_ref.mrc
MASK=$BASE/solvent_mask.mrc
STAR=$BASE/particles_wedge.star
OUT=$BASE/run_k2_blind
ITER="${ITER:-25}"
mkdir -p "$OUT"
echo "=== $(date +%H:%M:%S) RELION Class3D hc FM_easy K=2 BLIND (no GT, no firstiter_cc) ==="
"$RELION" \
  --i "$STAR" --ref "$REF" --o "$OUT/run" \
  --K 2 --iter "$ITER" --tau2_fudge 4 --ini_high 60 \
  --solvent_mask "$MASK" --flatten_solvent --zero_mask \
  --skip_align \
  --sym C1 --ctf --skip_subtomo_multi --pad 2 --random_seed 1 \
  --dont_combine_weights_via_disc --j 8 --gpu "" \
  > "$OUT/run.log" 2>&1
echo "=== DONE $(date +%H:%M:%S) -> $OUT ==="

GT=~/Research/synthetic_sta/motor_easy/hc_test_x6/subtomos/merged_AC_full/labels.csv
PY=~/conda-envs/relion-5.0/bin/python
# score the last iteration (blind classification has no GT-collapse 'iter1' special case)
LAST=$(ls "$OUT"/run_it*_data.star 2>/dev/null | sort | tail -1)
[ -n "$LAST" ] || { echo "no data.star produced"; exit 1; }
$PY - "$LAST" "$OUT/pred_blind.csv" <<'PYEOF'
import sys, os, csv
ds, out = sys.argv[1], sys.argv[2]
block=None; cols={}; data=[]
for line in open(ds):
    s=line.strip()
    if s.startswith("data_"): block=s; cols={}; continue
    if block=="data_particles":
        if s.startswith("_rln"): cols[s.split()[0]]=len(cols)
        elif s and not s.startswith(("loop","#")) and cols and len(s.split())>=len(cols):
            data.append(s.split())
ii=cols["_rlnImageName"]; ci=cols["_rlnClassNumber"]
with open(out,"w",newline="") as f:
    w=csv.writer(f); w.writerow(["file","pred_label"])
    for r in data: w.writerow([os.path.basename(r[ii]), r[ci]])
from collections import Counter
print("classes:", dict(Counter(r[ci] for r in data)), "n", len(data))
PYEOF
$PY scripts/eval/score_synthetic.py --pred "$OUT/pred_blind.csv" --gt "$GT" \
  --package relion --k 2 --run "k2_AC_hc_x6_542_BLIND" \
  --notes "BLIND global-avg init, no GT refs, no firstiter_cc; fair unsupervised; 2-class A/C x6 542p"
