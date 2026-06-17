#!/bin/bash
# PyTom auto_focus_classify on the REDESIGNED 2-class hc FM_easy (542 A/C), k=2.
# -a flag required: _swig_frm absent from pytom_env; particles are pre-aligned.
set -e
STA_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../../.." && pwd)"
AFC="$STA_DIR/packages/PyTom/T4P/scripts/auto_focus_classify_nofrm.py"
PL="$STA_DIR/packages/PyTom/FM_easy/configs/particle_list_motor_easy_hc.xml"
MASK="$STA_DIR/packages/PyTom/FM_easy/configs/motor_easy_hc_mask.em"
GT=~/Research/synthetic_sta/motor_easy/hc_test_x6/subtomos/merged_AC_full/labels.csv
PYTHON=~/conda-envs/eman2/bin/python3

echo "=== PyTom hc FM_easy k=2 ($(date +%H:%M:%S)) ==="
OUT_DIR="$STA_DIR/outputs/FM_easy/pytom/run_k2"
mkdir -p "$OUT_DIR"; cd "$OUT_DIR"
conda run -n pytom_env mpirun -np 16 "$AFC" \
    -p "$PL" -k 2 -f 20 -m "$MASK" -c "$MASK" -b 1 -i 15 -a -o ./ \
    2>&1 | tee pytom_motor_easy_hc_k2.log
echo "=== k=2 done ($(date +%H:%M:%S)) ==="

cd "$STA_DIR"
"$PYTHON" - <<PYEOF
import os, csv, glob, xml.etree.ElementTree as ET
out_dir = "$OUT_DIR"; gt_csv = "$GT"
xmls = sorted(glob.glob(os.path.join(out_dir, "classified_pl_iter*.xml")))
final_xml = xmls[-1]; print("Reading:", final_xml)
root = ET.parse(final_xml).getroot()
gt_files = [os.path.basename(r["file"]) for r in csv.DictReader(open(gt_csv))]
pred = {}
for p in root.iter("Particle"):
    fn = os.path.basename(p.get("Filename",""))
    c = p.find("Class")
    if c is not None: pred[fn] = int(c.get("Name",0)) + 1
out = "outputs/FM_easy/pytom/pytom_motor_easy_k2.csv"
with open(out,"w",newline="") as f:
    w=csv.writer(f); w.writerow(["file","pred_label"])
    for fn in gt_files: w.writerow([fn, pred.get(fn,1)])
from collections import Counter
print("counts:", dict(Counter(pred.values()))); print("Saved:", out)
PYEOF

"$PYTHON" scripts/eval/score_synthetic.py \
    --pred outputs/FM_easy/pytom/pytom_motor_easy_k2.csv --gt "$GT" \
    --package pytom --k 2 --run k2_AC_hc_x6_542 \
    --notes "auto_focus_classify -a; diff_sphere mask; 2-class A/C x6 542p"
echo "=== All done ($(date +%H:%M:%S)) ==="
