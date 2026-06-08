#!/bin/bash
# Run PyTom auto_focus_classify on motor_easy synthetic dataset (k=3 only).
# Uses RELION solvent mask (converted to EM), 694 pre-aligned particles.
# -a flag required: _swig_frm absent from pytom_env; particles are pre-aligned.
# Protocol: motor_easy uses k=3 (3 GT classes); T4P uses k=2.
set -e
STA_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
AFC="$STA_DIR/packages/PyTom/auto_focus_classify_nofrm.py"
PL="$STA_DIR/packages/PyTom/particle_list_motor_easy.xml"
MASK="$STA_DIR/packages/PyTom/motor_easy_mask.em"
GT=~/Research/synthetic_sta/motor_easy/production/subtomos/merged_all_aln/labels.csv
PYTHON=~/conda-envs/eman2/bin/python3

echo "=== PyTom motor_easy k=3 ($(date +%H:%M:%S)) ==="
mkdir -p "$STA_DIR/PyTom/motor_easy_k3"
cd "$STA_DIR/PyTom/motor_easy_k3"
conda run -n pytom_env mpirun -np 16 "$AFC" \
    -p "$PL" \
    -k 3 \
    -f 20 \
    -m "$MASK" \
    -c "$MASK" \
    -b 1 \
    -i 15 \
    -a \
    -o ./ \
    2>&1 | tee pytom_motor_easy_k3.log
echo "=== k=3 done ($(date +%H:%M:%S)) ==="

echo ""
echo "=== Scoring ==="
cd "$STA_DIR"
OUT_DIR="$STA_DIR/PyTom/motor_easy_k3"

"$PYTHON" - <<PYEOF
import os, csv, glob, xml.etree.ElementTree as ET

out_dir = "$OUT_DIR"
gt_csv = "$GT"

xmls = sorted(glob.glob(os.path.join(out_dir, "classified_pl_iter*.xml")))
if not xmls:
    print(f"No XML found in {out_dir}")
    exit(1)
final_xml = xmls[-1]
print(f"Reading: {final_xml}")

tree = ET.parse(final_xml)
root = tree.getroot()

gt_files = []
with open(gt_csv) as f:
    for row in csv.DictReader(f):
        gt_files.append(os.path.basename(row["file"]))

pred = {}
for particle in root.iter("Particle"):
    fname = os.path.basename(particle.get("Filename", ""))
    cls_el = particle.find("Class")
    if cls_el is not None:
        pred[fname] = int(cls_el.get("Name", 0)) + 1

pred_csv = os.path.join("outputs/relion_motor_easy", "pytom_motor_easy_k3.csv")
os.makedirs(os.path.dirname(pred_csv), exist_ok=True)
with open(pred_csv, "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["file", "pred_label"])
    for fname in gt_files:
        w.writerow([fname, pred.get(fname, 1)])
counts = {}
for v in pred.values():
    counts[v] = counts.get(v, 0) + 1
print(f"k=3 class counts: {dict(sorted(counts.items()))}")
print(f"Saved: {pred_csv}")
PYEOF

PRED="outputs/relion_motor_easy/pytom_motor_easy_k3.csv"
if [ -f "$PRED" ]; then
    "$PYTHON" scripts/eval/score_synthetic.py \
        --pred "$PRED" --gt "$GT" \
        --package pytom --k 3 --run "motor_easy_k3_v2mask"
fi

echo "=== All done ($(date +%H:%M:%S)) ==="
