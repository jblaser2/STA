#!/bin/bash
# RELION Class3D GT-seeded on the REDESIGNED 2-class hc FM_easy (542 A/C), K=2.
# GT-seeded (A,C class averages) + firstiter_cc; best result is iter1 (collapses after).
set -e
RELION=/home/jblaser2/relion-install/bin/relion_refine
BASE=outputs/FM_easy/relion
REFS=$BASE/class_refs.star
MASK=$BASE/solvent_mask.mrc
STAR=$BASE/particles_wedge.star
OUT=$BASE/run_k2
ITER="${ITER:-10}"
mkdir -p "$OUT"
echo "=== $(date +%H:%M:%S) RELION Class3D hc FM_easy K=2 GT-seeded firstiter_cc ==="
"$RELION" \
  --i "$STAR" --ref "$REFS" --o "$OUT/run" \
  --K 2 --iter "$ITER" --tau2_fudge 8 --ini_high 60 \
  --solvent_mask "$MASK" --flatten_solvent --zero_mask \
  --skip_align --firstiter_cc \
  --sym C1 --ctf --skip_subtomo_multi --pad 2 \
  --dont_combine_weights_via_disc --j 8 --gpu "" \
  > "$OUT/run.log" 2>&1
echo "=== DONE $(date +%H:%M:%S) -> $OUT ==="

GT=~/Research/synthetic_sta/motor_easy/hc_test_x6/subtomos/merged_AC_full/labels.csv
PY=~/conda-envs/relion-5.0/bin/python
for IT in 001 002; do
  DS="$OUT/run_it${IT}_data.star"
  [ -f "$DS" ] || continue
  $PY - "$DS" "$OUT/pred_iter${IT}.csv" <<'PYEOF'
import sys, os, csv
ds, out = sys.argv[1], sys.argv[2]
rows=[]; in_loop=False; cols={}; data=[]
for line in open(ds):
    s=line.strip()
    if s.startswith("_rln"):
        name=s.split()[0]; cols[name]=len(cols)
    elif s and not s.startswith(("data","loop","#","_")) and len(s.split())>=len(cols) and cols:
        data.append(s.split())
img_i=cols.get("_rlnImageName"); cls_i=cols.get("_rlnClassNumber")
with open(out,"w",newline="") as f:
    w=csv.writer(f); w.writerow(["file","pred_label"])
    for r in data:
        w.writerow([os.path.basename(r[img_i]), r[cls_i]])
print("wrote",out,len(data))
PYEOF
  $PY scripts/eval/score_synthetic.py --pred "$OUT/pred_iter${IT}.csv" --gt "$GT" \
    --package relion --k 2 --run "k2_AC_hc_x6_542_iter${IT}" \
    --notes "GT-seeded firstiter_cc K=2; 2-class A/C x6 542p; iter${IT}"
done
