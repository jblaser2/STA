#!/bin/bash
# DISCA on the REDESIGNED 2-class high-contrast FM_easy (542 A/C, x6, 96^3).
# Mask each 96^3 subtomo by the A-vs-C diff sphere, Fourier-crop to 32^3, k=2.
set -e
source ~/miniforge3/etc/profile.d/conda.sh; conda activate disca

MASK=~/Research/STA/packages/dynamo/dynamo_outputs/easy_pair_AC_hc/diff_sphere_r23_y55.mrc
SUBTOMO_DIR=~/Research/synthetic_sta/motor_easy/hc_test_x6/subtomos/merged_AC_full
PICKLE=~/Research/disca_work/disca_input_motor_easy_hc.pickle
OUTDIR=~/Research/disca_work/model_motor_easy_hc
TAG=motor_easy_hc_k2

echo "=== Building masked pickle ($(date +%H:%M:%S)) ==="
python ~/Research/STA/scripts/data_prep/build_disca_input.py \
    --subtomo-dir "$SUBTOMO_DIR" --mask "$MASK" --out "$PICKLE"

cd ~/Research/disca_work
echo "=== DISCA k=2 ($(date +%H:%M:%S)) ==="
DISCA_INPUT="$PICKLE" DISCA_K=2 DISCA_TAG="$TAG" DISCA_OUTDIR="$OUTDIR" \
  python torch_disca_run.py > log_motor_easy_hc_k2.txt 2>&1
echo "k=2 exit=$?"

echo "=== Convert labels -> file,pred_label CSV ($(date +%H:%M:%S)) ==="
python - "$SUBTOMO_DIR" "$OUTDIR/labels_${TAG}.pickle" <<'PY'
import os, sys, pickle, csv
subdir, labpath = sys.argv[1], sys.argv[2]
keys = sorted(os.path.splitext(f)[0] for f in os.listdir(subdir) if f.endswith('.mrc'))
lab = pickle.load(open(labpath, 'rb'))
lab = list(lab.values()) if isinstance(lab, dict) else list(lab)
assert len(keys) == len(lab), f"{len(keys)} keys vs {len(lab)} labels"
out = os.path.expanduser("~/Research/STA/outputs/FM_easy/disca/disca_motor_easy_k2.csv")
os.makedirs(os.path.dirname(out), exist_ok=True)
with open(out, 'w', newline='') as f:
    w = csv.writer(f); w.writerow(["file","pred_label"])
    for k, l in zip(keys, lab): w.writerow([k + ".mrc", int(l)])
print("wrote", out, len(keys), "rows")
PY
echo "ALL DONE $(date +%H:%M:%S)"
