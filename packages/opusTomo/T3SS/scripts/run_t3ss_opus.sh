#!/usr/bin/env bash
# OPUS-TOMO on T3SS injectisome (415 particles, 48^3, 13.33 A/px).
# Junk protocol: k=3 run; k=2 evaluates B vs C.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../../.." && pwd)"
PROJ_DIR="$SCRIPT_DIR/opus_project_t3ss"
LOG="$PROJ_DIR/run.log"

PARTICLE_DIR="$HOME/Research/synthetic_sta/injectisome/subtomos/merged_BC_t3ss"
GT_LABELS="$PARTICLE_DIR/labels.csv"

K=${1:-3}
EPOCH=""
SKIP_TRAIN=0

while [[ $# -gt 0 ]]; do
    case "$1" in
        --k)          K="$2";       shift 2 ;;
        --epoch)      EPOCH="$2";   shift 2 ;;
        --skip-train) SKIP_TRAIN=1; shift ;;
        *) shift ;;
    esac
done

log() { echo "[$(date '+%H:%M:%S')] $*" | tee -a "$LOG"; }
run_step() { local label="$1"; shift; log "=== $label ==="; "$@" 2>&1 | tee -a "$LOG"; log "--- done ---"; }

source ~/miniforge3/etc/profile.d/conda.sh
conda activate opuset
mkdir -p "$PROJ_DIR"; echo "" >> "$LOG"
log "Pipeline started (K=$K)"

[[ -f "$PROJ_DIR/particles.star" ]] || \
    run_step "Write STAR" python "$SCRIPT_DIR/setup_t3ss_opus.py" "$PROJ_DIR"

[[ -f "$PROJ_DIR/pose_euler.pkl" ]] || \
    run_step "Parse poses" dsd parse_pose_star "$PROJ_DIR/particles.star" \
        -D 48 --Apix 13.33 -o "$PROJ_DIR/pose_euler.pkl"

# Build consensus + threshold mask
if [[ ! -f "$PROJ_DIR/mask.mrc" ]]; then
    run_step "Consensus + mask" python - <<PYEOF
import os, glob, numpy as np, mrcfile
from scipy.ndimage import binary_dilation
pdir = '$PARTICLE_DIR'; proj = '$PROJ_DIR'
files = sorted(glob.glob(os.path.join(pdir, 'subtomo_*.mrc')))
acc = None
for f in files:
    with mrcfile.open(f, permissive=True) as m: v = m.data.astype(np.float32)
    acc = v.copy() if acc is None else acc + v
avg = acc / len(files)
with mrcfile.new(os.path.join(proj,'consensus.mrc'),overwrite=True) as m: m.set_data(avg); m.voxel_size=13.33
mask = (avg > avg.mean() + avg.std()).astype(np.float32)
mask = binary_dilation(mask, iterations=2).astype(np.float32)
with mrcfile.new(os.path.join(proj,'mask.mrc'),overwrite=True) as m: m.set_data(mask); m.voxel_size=13.33
print(f'Mask: {100*mask.mean():.1f}% voxels')
PYEOF
fi

OUTDIR="$PROJ_DIR/output"
if [[ $SKIP_TRAIN -eq 1 ]]; then
    log "Training skipped."
elif ls "$OUTDIR"/z.*.pkl 2>/dev/null | grep -q .; then
    log "z.*.pkl exists, skipping training."
else
    mkdir -p "$OUTDIR"
    run_step "Train OPUS-ET (20 epochs)" \
        dsd train_tomo "$PROJ_DIR/particles.star" \
            --poses "$PROJ_DIR/pose_euler.pkl" \
            -n 20 -b 16 --zdim 8 --zaffinedim 0 \
            --lr 1e-4 --beta-control 1.0 --lamb 0 \
            -o "$OUTDIR" \
            -r "$PROJ_DIR/mask.mrc" \
            --downfrac 1.0 --templateres 64 \
            --angpix 13.33 \
            --datadir "$PARTICLE_DIR" \
            --ctfalpha 0. --ctfbeta 0. \
            --split "$OUTDIR/split.pkl"
fi

[[ -n "$EPOCH" ]] || EPOCH=$(ls "$OUTDIR"/z.*.pkl 2>/dev/null | sed 's/.*z\.\([0-9]*\)\.pkl/\1/' | sort -n | tail -1)
[[ -n "$EPOCH" ]] || { log "ERROR: No z.*.pkl found"; exit 1; }
log "Using epoch $EPOCH"

ANALYZE_DIR="$OUTDIR/analyze.${EPOCH}"
[[ -d "$ANALYZE_DIR/kmeans${K}" ]] || \
    run_step "Analyze (K=$K)" dsdsh analyze "$OUTDIR" "$EPOCH" 2 "$K"

[[ -f "$ANALYZE_DIR/kmeans${K}/reference0.mrc" ]] || \
    run_step "Generate volumes" dsdsh eval_vol "$OUTDIR" "$EPOCH" kmeans "$K" 13.33

RESULT_CSV="$REPO_ROOT/outputs/T3SS/opus/opus_t3ss_k${K}.csv"
log "=== Extract labels -> $RESULT_CSV ==="
python - <<PYEOF 2>&1 | tee -a "$LOG"
import os, pickle, csv
from collections import Counter
from sklearn.metrics import adjusted_rand_score

proj_dir    = '$PROJ_DIR'
analyze_dir = '$ANALYZE_DIR'
k           = $K
result_csv  = '$RESULT_CSV'
gt_csv      = '$GT_LABELS'

labels_path = os.path.join(analyze_dir, f'kmeans{k}', 'labels.pkl')
star_path   = os.path.join(proj_dir, 'particles.star')

labels = pickle.load(open(labels_path, 'rb'))
filenames = []
with open(star_path) as f:
    for line in f:
        s = line.strip()
        if s and not s.startswith(('#','data','loop','_')):
            parts = s.split()
            if parts: filenames.append(parts[0])

if len(filenames) != len(labels):
    raise ValueError(f'Mismatch: {len(filenames)} vs {len(labels)}')

os.makedirs(os.path.dirname(os.path.abspath(result_csv)), exist_ok=True)
with open(result_csv, 'w', newline='') as f:
    w = csv.writer(f); w.writerow(['file','pred_label'])
    for fn, lb in zip(filenames, labels): w.writerow([fn, int(lb)])

rows = list(csv.DictReader(open(gt_csv)))
gt_map = {r['file']: r['label'] for r in rows}
signal = [r['file'] for r in rows if r['label'] in ('class_B','class_C')]
gt_sig = [gt_map[f] for f in signal]
pred_map = {fn: int(lb) for fn, lb in zip(filenames, labels)}
pr_sig = [pred_map.get(f, 0) for f in signal]
ari = adjusted_rand_score(gt_sig, pr_sig)
print(f'K={k} dist: {dict(sorted(Counter(int(l) for l in labels).items()))}')
print(f'ARI(B/C)={ari:.3f}')
print(f'Saved {len(labels)} rows -> {result_csv}')
PYEOF
log "Pipeline complete."
