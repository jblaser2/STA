#!/bin/bash
# EMAN2 T3SS PCA classification pipeline -- NO ALIGNMENT variant.
# 415 particles (48^3, 13.33 A/px): 215 class_B + 120 class_C + 80 junk.
# Junk protocol: k=3 run; k=2 evaluates only B vs C.
set -euo pipefail

CONDA_BASE="/home/jblaser2/miniforge3"
PROJECT_DIR="/home/jblaser2/Research/eman2_t3ss"
SCRIPTS_DIR="/home/jblaser2/Research/STA/packages/eman2/T3SS/scripts"
T4P_SCRIPTS="/home/jblaser2/Research/STA/packages/eman2/T4P/scripts"

NCLASS=${1:-3}        # default k=3 (B + C + junk); pass 2 for blind B vs C
NBASIS=12
MAXRES=80             # low-pass in Å before PCA
SYM=c1
THREADS=20
CLEAN=1
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

cd "$PROJECT_DIR"
log "Working in $PROJECT_DIR  k=$NCLASS"

# Symlink helper scripts from T4P (identical implementation)
for s in make_identity_parms.py patch_scripts.py plot_pca.py plot_class_averages.py; do
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
    log "  Averaging (mean.tomo, identity orientation) → $comb"
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

CLEAN_FLAG=""
[ "$CLEAN" -eq 1 ] && CLEAN_FLAG="--clean"

log "Step 4: PCA classification (nclass=$NCLASS, nbasis=$NBASIS, maxres=$MAXRES A)..."
{ e2spt_pcasplit.py \
    --path "$CONS_PATH" --iter "$CONS_ITER" \
    --nclass "$NCLASS" --nbasis "$NBASIS" --maxres "$MAXRES" \
    --sym "$SYM" --mask "$CONS_MASK" --nowedgefill --verbose 1 \
    $CLEAN_FLAG \
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

log "=== Pipeline complete. SPTCLS=$SPTCLS ==="
