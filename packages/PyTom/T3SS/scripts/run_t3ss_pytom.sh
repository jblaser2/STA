#!/bin/bash
# PyTom auto_focus_classify on T3SS injectisome dataset (415 particles, 48^3).
# -a flag required: _swig_frm absent; particles are pre-aligned.
# Junk protocol: k=3 run (B + C + junk); k=2 for blind B/C comparison.
set -e
STA_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../../.." && pwd)"
AFC="$STA_DIR/packages/PyTom/T4P/scripts/auto_focus_classify_nofrm.py"
PL="$STA_DIR/packages/PyTom/T3SS/configs/particle_list_t3ss.xml"
MASK="$STA_DIR/packages/PyTom/T3SS/configs/mask_t3ss.em"
GT=~/Research/synthetic_sta/injectisome/subtomos/merged_BC_t3ss/labels.csv
PYTHON=~/conda-envs/eman2/bin/python3
K=${1:-2}

echo "=== PyTom T3SS k=$K ($(date +%H:%M:%S)) ==="
OUT_DIR="$STA_DIR/outputs/T3SS/pytom/run_k${K}"
mkdir -p "$OUT_DIR"; cd "$OUT_DIR"

conda run -n pytom_env mpirun -np 16 "$AFC" \
    -p "$PL" -k $K -f 20 -m "$MASK" -c "$MASK" -b 1 -i 15 -a -o ./ \
    2>&1 | tee pytom_t3ss_k${K}.log

echo "=== k=$K done ($(date +%H:%M:%S)) ==="

# Score
"$PYTHON" - <<PYEOF
import os, csv, glob, xml.etree.ElementTree as ET
from sklearn.metrics import adjusted_rand_score

out_dir = "$OUT_DIR"; gt_csv = "$GT"; K = $K
xmls = sorted(glob.glob(os.path.join(out_dir, "classified_pl_iter*.xml")))
if not xmls: print("ERROR: no classified_pl_iter*.xml found"); exit(1)
final_xml = xmls[-1]; print("Reading:", final_xml)
root = ET.parse(final_xml).getroot()

rows = list(csv.DictReader(open(gt_csv)))
gt_map = {r["file"]: r["label"] for r in rows}
pred = {}
for p in root.iter("Particle"):
    fn = os.path.basename(p.get("Filename",""))
    c = p.find("Class")
    if c is not None: pred[fn] = int(c.get("Name",0)) + 1

signal = [r["file"] for r in rows if r["label"] in ("class_B","class_C")]
gt_sig  = [gt_map[f] for f in signal]
pr_sig  = [pred.get(f, 1) for f in signal]
ari = adjusted_rand_score(gt_sig, pr_sig)

from collections import Counter
print(f"PyTom T3SS k={K}: ARI(B/C)={ari:.3f}  counts={dict(Counter(pred.values()))}")

out = os.path.join("$STA_DIR", f"outputs/T3SS/pytom/pytom_t3ss_k{K}.csv")
os.makedirs(os.path.dirname(out), exist_ok=True)
with open(out,"w",newline="") as f:
    w=csv.writer(f); w.writerow(["file","pred_label"])
    for row in rows: w.writerow([row["file"], pred.get(row["file"],1)])
print("Saved:", out)
PYEOF
echo "=== All done ($(date +%H:%M:%S)) ==="
