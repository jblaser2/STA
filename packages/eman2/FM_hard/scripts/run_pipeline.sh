#!/bin/bash
# EMAN2 FM_hard PCA classification -- 813 particles, k=3, no junk.
# 3 classes: base / basal_body / mature (271 each), 96^3, 13.33 A/px.
set -euo pipefail

CONDA_BASE="/home/jblaser2/miniforge3"
PROJECT_DIR="/home/jblaser2/Research/eman2_fm_hard"
SCRIPTS_DIR="/home/jblaser2/Research/STA/packages/eman2/FM_hard/scripts"
T4P_SCRIPTS="/home/jblaser2/Research/STA/packages/eman2/T4P/scripts"

NCLASS=3
NBASIS=12
MAXRES=80
SYM=c1
THREADS=20
NONINTERACTIVE=1

CONS_PATH="spt_noalign"
CONS_ITER=1
CONS_ITER2=$(printf "%02d" "$CONS_ITER")
CONS_PARMS="${CONS_PATH}/particle_parms_${CONS_ITER2}.json"
CONS_MAP="${CONS_PATH}/threed_${CONS_ITER2}.hdf"
CONS_MASK="${CONS_PATH}/mask_tight.hdf"

log() { echo "[$(date '+%H:%M:%S')] $*"; }

source "$CONDA_BASE/etc/profile.d/conda.sh"
conda activate eman2
export PATH="$CONDA_BASE/envs/eman2/bin:$PATH"

mkdir -p "$PROJECT_DIR"
cd "$PROJECT_DIR"
log "Working in $PROJECT_DIR  k=$NCLASS"

for s in make_identity_parms.py patch_scripts.py; do
    [ -L "$s" ] || ln -sf "$T4P_SCRIPTS/$s" "$s"
done

noalign_average() {
    local path="$1" itr="$2" lst="${3:-}"
    local itr2; itr2=$(printf "%02d" "$itr")
    local parms="${path}/particle_parms_${itr2}.json"
    local even="${path}/threed_${itr2}_even.hdf"
    local comb="${path}/threed_${itr2}.hdf"
    mkdir -p "$path"
    if [ ! -f "$parms" ]; then
        [ -n "$lst" ] || { echo "ERROR: noalign_average needs an lst"; exit 1; }
        log "  Writing identity particle_parms → $parms"
        python make_identity_parms.py "$lst" "$parms"
    fi
    log "  Averaging → $comb"
    { e2spt_average.py --path "$path" --iter "$itr" --sym "$SYM" \
        --keep 1.0 --threads "$THREADS" --skippostp --verbose 1; } 255>&-
    log "  Post-processing for $path iter $itr2"
    { e2refine_postprocess.py --even "$even" --odd "${path}/threed_${itr2}_odd.hdf" \
        --output "$comb" --iter "$itr" --tomo --mass -1 \
        --threads "$THREADS" --restarget 30 --sym "$SYM" --align; } 255>&-
}

log "Step 1: Patching e2spt_pcasplit.py..."
python patch_scripts.py

if [ -f particles.hdf ] && [ -f ptcls.lst ]; then
    log "Step 2: Data files exist — skipping ingestion."
else
    log "Step 2: Building HDF stack..."
    python "$SCRIPTS_DIR/make_project.py"
fi

if [ -f "$CONS_MAP" ] && [ -f "$CONS_MASK" ] && [ -f "$CONS_PARMS" ]; then
    log "Step 3: Consensus average exists — skipping."
else
    log "Step 3: Building consensus average..."
    noalign_average "$CONS_PATH" "$CONS_ITER" ptcls.lst
fi

log "Step 4: PCA classification (nclass=$NCLASS, nbasis=$NBASIS, maxres=$MAXRES A)..."
{ e2spt_pcasplit.py \
    --path "$CONS_PATH" --iter "$CONS_ITER" \
    --nclass "$NCLASS" --nbasis "$NBASIS" --maxres "$MAXRES" \
    --sym "$SYM" --mask "$CONS_MASK" --nowedgefill --verbose 1 \
    2>&1 | tee pca_classify_k${NCLASS}.log; } 255>&-

SPTCLS=$(ls -d sptcls_* 2>/dev/null | sort | tail -1)
[ -n "$SPTCLS" ] || { echo "ERROR: No sptcls_XX directory found"; exit 1; }
log "Output: $SPTCLS/"
wc -l "$SPTCLS"/ptcls_cls*.lst

log "Step 5: Per-class averaging..."
for CLS_LST in "$SPTCLS"/ptcls_cls*.lst; do
    CLS_NUM=$(basename "$CLS_LST" | sed 's/ptcls_cls\([0-9]*\)\.lst/\1/')
    CLS_ITR=$((10#$CLS_NUM))
    noalign_average "$SPTCLS" "$CLS_ITR"
    [ -f "$SPTCLS/mask.hdf" ] && cp -f "$SPTCLS/mask.hdf" "$SPTCLS/mask_cls$(printf "%02d" $CLS_ITR).hdf"
done

log "Step 6: Score against GT..."
conda run -n eman2 python3 "$SCRIPTS_DIR/score_eman2_fm_hard.py" "$PROJECT_DIR" "$SPTCLS"

log "=== Pipeline complete. SPTCLS=$SPTCLS ==="
