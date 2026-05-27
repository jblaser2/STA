#!/bin/bash
# EMAN2 subtomogram PCA classification pipeline
# Usage: ./run_pipeline.sh
set -euo pipefail

CONDA_BASE="/home/ejl62/miniforge3"
PROJECT_DIR="/home/ejl62/src/eman2_project"

# ---- Parameters (edit these before running) ----
NCLASS=2      # number of classes for K-Means
NBASIS=8      # number of PCA basis vectors
MAXRES=30     # low-pass filter resolution before PCA (Angstroms)
SYM=c1        # symmetry
THREADS=24    # CPU threads for refinement
CLEAN=0       # 1 = remove outliers before PCA (--clean flag)
# -------------------------------------------------

log() { echo "[$(date '+%H:%M:%S')] $*"; }

# ---- Activate eman2 conda environment ----
source "$CONDA_BASE/etc/profile.d/conda.sh"
conda activate eman2
# Ensure eman2 binaries take priority over system Python
export PATH="$CONDA_BASE/envs/eman2/bin:$PATH"

cd "$PROJECT_DIR"
log "Working in $PROJECT_DIR"
log "EMAN2 Python: $(which python)"

# ---- Step 1: Patch np.int → np.int64 in e2spt_pcasplit.py ----
log "Step 1: Checking/patching e2spt_pcasplit.py..."
python patch_scripts.py

# ---- Step 2: Data ingestion ----
if [ -f particles.hdf ] && [ -f ptcls.lst ] && [ -f initial_ref.hdf ]; then
    log "Step 2: Data files already exist — skipping ingestion."
else
    log "Step 2: Stacking MRC particles into HDF + building particle list..."
    python make_project.py
fi

for f in particles.hdf ptcls.lst initial_ref.hdf; do
    [ -f "$f" ] || { echo "ERROR: $f not found after ingestion"; exit 1; }
done

# ---- Step 3: Refinement (1 iteration to generate alignment metadata) ----
if [ -f spt_01/particle_parms_01.json ]; then
    log "Step 3: spt_01/particle_parms_01.json exists — skipping refinement."
else
    log "Step 3: Running 1-iteration refinement (threads=$THREADS)..."
    log "        This takes ~15–30 minutes. Log → refine.log"
    { e2spt_refine.py ptcls.lst \
        --ref initial_ref.hdf \
        --path spt_01 \
        --niter 1 \
        --sym "$SYM" \
        --threads "$THREADS" \
        --verbose 1 \
        2>&1 | tee refine.log; } 255>&-
    log "Refinement done."
fi

[ -f spt_01/particle_parms_01.json ] || { echo "ERROR: refinement failed — particle_parms_01.json missing"; exit 1; }
[ -f spt_01/mask_tight.hdf ] || log "WARNING: mask_tight.hdf not found — pcasplit will fail. Check refine.log."

# ---- Step 4: PCA classification (interactive loop) ----
SPTCLS=""

while true; do
    CLEAN_FLAG=""
    [ "$CLEAN" -eq 1 ] && CLEAN_FLAG="--clean"

    log "Step 4: PCA classification (nclass=$NCLASS, nbasis=$NBASIS, maxres=$MAXRES Å, clean=$CLEAN)..."
    { e2spt_pcasplit.py \
        --path spt_01 \
        --iter 1 \
        --nclass "$NCLASS" \
        --nbasis "$NBASIS" \
        --maxres "$MAXRES" \
        --sym "$SYM" \
        --nowedgefill \
        --verbose 1 \
        $CLEAN_FLAG \
        2>&1 | tee pca_classify.log; } 255>&-

    # Find the output directory created by this run (latest sptcls_XX)
    SPTCLS=$(ls -d sptcls_* 2>/dev/null | sort | tail -1)
    [ -n "$SPTCLS" ] || { echo "ERROR: No sptcls_XX directory found"; exit 1; }

    log "Output: $SPTCLS/"

    # ---- Step 5: Plot PCA scatter and class average images ----
    log "Step 5: Plotting PCA scatter..."
    python plot_pca.py "$SPTCLS/pca_ptcls.txt"

    log "Step 5b: Saving class average slice images..."
    python plot_class_averages.py "$SPTCLS"

    echo ""
    echo "========================================================"
    echo " Scatter plot:    $SPTCLS/pca_scatter.png"
    echo " Class averages:  $SPTCLS/class_averages.png"
    echo ""
    echo " Particle counts per class:"
    wc -l "$SPTCLS"/ptcls_cls*.lst
    echo ""
    echo " View class averages:"
    echo "   e2display.py $SPTCLS/threed_*.hdf"
    echo "========================================================"

    # Try to open the scatter plot automatically
    for viewer in eog xdg-open display; do
        if command -v "$viewer" &>/dev/null 2>&1; then
            "$viewer" "$SPTCLS/pca_scatter.png" &
            break
        fi
    done

    echo ""
    echo "Options:"
    echo "  [Enter]   Accept — exit the loop"
    echo "  n <N>     Change --nclass to N (e.g. 'n 3')"
    echo "  b <N>     Change --nbasis to N (e.g. 'b 10')"
    echo "  r <N>     Change --maxres to N Å  (e.g. 'r 40')"
    echo "  c         Toggle --clean (currently: $CLEAN)"
    echo "  q         Quit without saving"
    echo ""
    read -r -p "Enter option: " USER_INPUT || true

    if [ -z "${USER_INPUT:-}" ]; then
        log "Classification accepted."
        break
    fi

    CMD=$(echo "$USER_INPUT" | awk '{print $1}')
    VAL=$(echo "$USER_INPUT" | awk '{$1=""; print $0}' | xargs 2>/dev/null || true)

    case "$CMD" in
        n) NCLASS="$VAL"; log "nclass → $NCLASS" ;;
        b) NBASIS="$VAL"; log "nbasis → $NBASIS" ;;
        r) MAXRES="$VAL"; log "maxres → $MAXRES Å" ;;
        c) [ "$CLEAN" -eq 0 ] && CLEAN=1 || CLEAN=0; log "--clean → $CLEAN" ;;
        q) log "Quit."; exit 0 ;;
        *) echo "Unknown option. Press Enter to accept or use n/b/r/c/q." ;;
    esac
done

# ---- Final summary ----
echo ""
log "=== Pipeline complete ==="
echo ""
echo "Final results: $SPTCLS/"
echo ""
echo "Particle counts:"
wc -l "$SPTCLS"/ptcls_cls*.lst
echo ""
echo "View class averages:"
echo "  e2display.py $SPTCLS/threed_*.hdf"
echo ""
echo "Per-class refinement commands (optional):"
for i in $(seq 1 "$NCLASS"); do
    CLS=$(printf "%02d" "$i")
    echo "  e2spt_refine.py $SPTCLS/ptcls_cls$CLS.lst \\"
    echo "    --ref $SPTCLS/threed_$CLS.hdf \\"
    echo "    --path spt_cls$CLS --niter 3 --sym $SYM --threads $THREADS --goldstandard 30 --verbose 1"
done
