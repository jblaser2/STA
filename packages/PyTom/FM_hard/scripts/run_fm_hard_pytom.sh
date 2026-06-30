#!/bin/bash
# PyTom auto_focus_classify on FM_hard (813 particles, 96^3, k=3).
# -a flag required (FRM mode). Mask: diff_mask_hard.mrc -> .em.
set -e
STA_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../../.." && pwd)"
AFC="$STA_DIR/packages/PyTom/T4P/scripts/auto_focus_classify_nofrm.py"
SETUP="$STA_DIR/packages/PyTom/FM_hard/scripts/setup_fm_hard_pytom.py"
PL="$STA_DIR/packages/PyTom/FM_hard/configs/particle_list_fm_hard.xml"
MASK="$STA_DIR/packages/PyTom/FM_hard/configs/diff_mask_hard.em"
GT=~/Research/synthetic_sta/motor_hard/subtomos/merged_ABC_full/labels.csv
PYTHON=~/conda-envs/eman2/bin/python3

echo "=== Step 1: Setup ($(date +%H:%M:%S)) ==="
conda run -n pytom_env python3 "$SETUP"

for K in 3; do
    echo "=== PyTom FM_hard k=$K ($(date +%H:%M:%S)) ==="
    OUT_DIR="$STA_DIR/outputs/FM_hard/pytom/run_k${K}"
    mkdir -p "$OUT_DIR"; cd "$OUT_DIR"
    conda run -n pytom_env mpirun -np 16 "$AFC" \
        -p "$PL" -k $K -f 20 -m "$MASK" -c "$MASK" -b 1 -i 15 -a -o ./ \
        2>&1 | tee pytom_fm_hard_k${K}.log
    echo "=== k=$K done ($(date +%H:%M:%S)) ==="

    cd "$STA_DIR"
    mkdir -p outputs/FM_hard/pytom
    "$PYTHON" - <<PYEOF
import os, csv, glob, xml.etree.ElementTree as ET
out_dir = "$OUT_DIR"; gt_csv = "$GT"; k = $K
xmls = sorted(glob.glob(os.path.join(out_dir, "classified_pl_iter*.xml")))
final_xml = xmls[-1]; print("Reading:", final_xml)
root = ET.parse(final_xml).getroot()
gt_rows = list(csv.DictReader(open(gt_csv)))
gt_map  = {r['file']: r['label'] for r in gt_rows}
files   = [r['file'] for r in gt_rows]
pred = {}
for p in root.iter("Particle"):
    fn = os.path.basename(p.get("Filename",""))
    c = p.find("Class")
    if c is not None: pred[fn] = int(c.get("Name",0)) + 1

pred_csv = "outputs/FM_hard/pytom/pytom_fm_hard_k${K}.csv"
with open(pred_csv, "w", newline="") as f:
    w=csv.writer(f); w.writerow(["file","pred_label"])
    for fn in files: w.writerow([fn, pred.get(fn,1)])

from sklearn.metrics import adjusted_rand_score
from collections import Counter
gt_list = [gt_map[f] for f in files]
pr_list = [pred.get(f,1) for f in files]
ari = adjusted_rand_score(gt_list, pr_list)
print(f"PyTom FM_hard k={k}: ARI={ari:.3f}  counts={dict(Counter(pr_list))}")
print(f"Saved: {pred_csv}")
PYEOF
done

echo "=== All done ($(date +%H:%M:%S)) ==="
