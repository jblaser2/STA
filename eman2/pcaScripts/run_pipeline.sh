#!/bin/bash
# EMAN2 subtomogram PCA classification pipeline
# Usage: ./run_pipeline.sh
set -euo pipefail

CONDA_BASE="/home/ejl62/miniforge3"
PROJECT_DIR="/home/ejl62/src/eman2_project"

# ---- Parameters (edit these before running) ----
NCLASS=2              # number of K-Means clusters
NBASIS=12             # PCA basis vectors (loosened from 8 to capture subtler variance)
MAXRES=60             # low-pass before PCA in Å (loosened from 30; matches actual signal range)
SYM=c1                # symmetry
THREADS=24            # CPU threads for all refinement steps
CLEAN=1               # 1 = --clean removes PCA outliers before K-Means
PKEEP=0.8             # fraction of best-scoring particles to average (0.7–0.8 typical)

SEED_N=50             # particles used for seed refinement (Step 3a)
SEED_NITER=5          # iterations for seed refinement
NITER=10              # full-dataset refinement iterations (Step 3b)
GOLDSTANDARD=30       # Å — phase-randomisation cutoff for full refinement

NITER_PERCLASS=5      # per-class refinement iterations (Step 6)
GOLDSTANDARD_PERCLASS=20  # Å — gold-standard cutoff for per-class refinement
# -------------------------------------------------

# Derived paths — do not edit these
SEED_LST="subset${SEED_N}.lst"
SEED_PATH="spt_seed"
SEED_REF="${SEED_PATH}/threed_$(printf "%02d" "${SEED_NITER}").hdf"
REFINE_PATH="spt_02"
FINAL_PARMS="${REFINE_PATH}/particle_parms_$(printf "%02d" "${NITER}").json"

log() { echo "[$(date '+%H:%M:%S')] $*"; }

# ---- Activate eman2 conda environment ----
source "$CONDA_BASE/etc/profile.d/conda.sh"
conda activate eman2
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

# ---- Step 3a: Seed reference from a particle subset ----
# Refine SEED_N particles for SEED_NITER iterations to produce a structurally
# meaningful starting reference. A direct arithmetic mean of all particles is a
# featureless blob; even a short refinement on a small subset produces a much
# better seed because particles are averaged in a common orientation frame.
if [ -f "$SEED_REF" ]; then
    log "Step 3a: Seed reference exists ($SEED_REF) — skipping."
else
    if [ ! -f "$SEED_LST" ]; then
        log "Step 3a: Building ${SEED_N}-particle subset (${SEED_LST})..."
        python3 -c "
from EMAN2 import LSXFile
n = $SEED_N
src = LSXFile('ptcls.lst', True)
dst = LSXFile('$SEED_LST', False)
for i in range(n):
    entry = src.read(i)
    dst.write(-1, entry[0], entry[1])
src.close(); dst.close()
print('Created $SEED_LST ({} particles)'.format(n))
"
    fi

    log "Step 3a: Running ${SEED_NITER}-iteration seed refinement on ${SEED_N} particles..."
    log "         Log → seed_refine.log"
    { e2spt_refine.py "$SEED_LST" \
        --ref initial_ref.hdf \
        --path "$SEED_PATH" \
        --niter "$SEED_NITER" \
        --sym "$SYM" \
        --threads "$THREADS" \
        --pkeep "$PKEEP" \
        --verbose 1 \
        2>&1 | tee seed_refine.log; } 255>&-
    log "Seed refinement done. Reference: $SEED_REF"
fi

[ -f "$SEED_REF" ] || { echo "ERROR: Seed reference missing: $SEED_REF"; exit 1; }

# ---- Step 3b: Full-dataset refinement ----
# 10 iterations with gold-standard FSC. Uses the seed reference from Step 3a
# as the starting point rather than the featureless arithmetic mean.
if [ -f "$FINAL_PARMS" ]; then
    log "Step 3b: $FINAL_PARMS exists — skipping full refinement."
else
    log "Step 3b: Running ${NITER}-iteration full refinement..."
    log "         Seed:         $SEED_REF"
    log "         Gold-standard: ${GOLDSTANDARD} Å"
    log "         pkeep:         ${PKEEP}"
    log "         Threads:       ${THREADS}"
    log "         This may take several hours. Log → refine.log"
    { e2spt_refine.py ptcls.lst \
        --ref "$SEED_REF" \
        --path "$REFINE_PATH" \
        --niter "$NITER" \
        --sym "$SYM" \
        --threads "$THREADS" \
        --pkeep "$PKEEP" \
        --goldstandard "$GOLDSTANDARD" \
        --verbose 1 \
        2>&1 | tee refine.log; } 255>&-
    log "Full refinement done."
fi

[ -f "$FINAL_PARMS" ] || { echo "ERROR: Full refinement failed — $FINAL_PARMS missing"; exit 1; }

if [ ! -f "$REFINE_PATH/mask_tight.hdf" ]; then
    log "WARNING: $REFINE_PATH/mask_tight.hdf not found — pcasplit will run without a mask."
    log "         Check refine.log for post-processing errors."
fi

# Print FSC summary from full refinement
FULL_RES=$(grep "Resolution.*FSC" refine.log 2>/dev/null | tail -1 || true)
[ -n "$FULL_RES" ] && log "Full refinement resolution: $FULL_RES"

# ---- Step 4: PCA classification (interactive loop) ----
SPTCLS=""

while true; do
    CLEAN_FLAG=""
    [ "$CLEAN" -eq 1 ] && CLEAN_FLAG="--clean"

    log "Step 4: PCA classification (nclass=$NCLASS, nbasis=$NBASIS, maxres=$MAXRES Å, clean=$CLEAN)..."
    { e2spt_pcasplit.py \
        --path "$REFINE_PATH" \
        --iter "$NITER" \
        --nclass "$NCLASS" \
        --nbasis "$NBASIS" \
        --maxres "$MAXRES" \
        --sym "$SYM" \
        --nowedgefill \
        --verbose 1 \
        $CLEAN_FLAG \
        2>&1 | tee pca_classify.log; } 255>&-

    SPTCLS=$(ls -d sptcls_* 2>/dev/null | sort | tail -1)
    [ -n "$SPTCLS" ] || { echo "ERROR: No sptcls_XX directory found"; exit 1; }
    log "Output: $SPTCLS/"

    # ---- Step 5: Visualisation ----
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
    echo "========================================================"

    for viewer in eog xdg-open display; do
        if command -v "$viewer" &>/dev/null 2>&1; then
            "$viewer" "$SPTCLS/pca_scatter.png" &
            break
        fi
    done

    echo ""
    echo "Options:"
    echo "  [Enter]   Accept — proceed to per-class refinement"
    echo "  n <N>     Change --nclass (e.g. 'n 3')"
    echo "  b <N>     Change --nbasis (e.g. 'b 10')"
    echo "  r <N>     Change --maxres in Å (e.g. 'r 80')"
    echo "  c         Toggle --clean (currently: $CLEAN)"
    echo "  q         Quit without proceeding"
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

# ---- Step 6: Per-class refinement ----
log "Step 6: Per-class refinement (${NITER_PERCLASS} iters each, goldstandard=${GOLDSTANDARD_PERCLASS} Å)..."
echo ""

for CLS_LST in "$SPTCLS"/ptcls_cls*.lst; do
    CLS_NUM=$(basename "$CLS_LST" | sed 's/ptcls_cls\([0-9]*\)\.lst/\1/')
    CLS_REF="$SPTCLS/threed_${CLS_NUM}.hdf"
    CLS_PATH="spt_cls${CLS_NUM}"
    FINAL_CLS="${CLS_PATH}/threed_$(printf "%02d" "${NITER_PERCLASS}").hdf"
    N_PTCLS=$(wc -l < "$CLS_LST")

    if [ -f "$FINAL_CLS" ]; then
        log "  Class $CLS_NUM: $FINAL_CLS already exists — skipping."
        continue
    fi

    log "  Class $CLS_NUM: Refining $N_PTCLS particles → $CLS_PATH/ ..."
    log "           Log → refine_cls${CLS_NUM}.log"
    { e2spt_refine.py "$CLS_LST" \
        --ref "$CLS_REF" \
        --path "$CLS_PATH" \
        --niter "$NITER_PERCLASS" \
        --sym "$SYM" \
        --threads "$THREADS" \
        --pkeep "$PKEEP" \
        --goldstandard "$GOLDSTANDARD_PERCLASS" \
        --verbose 1 \
        2>&1 | tee "refine_cls${CLS_NUM}.log"; } 255>&-
    log "  Class $CLS_NUM done."
done

# ---- Final summary ----
echo ""
log "=== Pipeline complete ==="
echo ""
echo "Full refinement:  $REFINE_PATH/  ($NITER iterations, goldstandard=${GOLDSTANDARD} Å)"
echo "  $FULL_RES"
echo ""
echo "Classification:   $SPTCLS/"
echo ""
echo "Per-class results:"
for CLS_LST in "$SPTCLS"/ptcls_cls*.lst; do
    CLS_NUM=$(basename "$CLS_LST" | sed 's/ptcls_cls\([0-9]*\)\.lst/\1/')
    CLS_PATH="spt_cls${CLS_NUM}"
    FINAL_CLS="${CLS_PATH}/threed_$(printf "%02d" "${NITER_PERCLASS}").hdf"
    N_PTCLS=$(wc -l < "$CLS_LST")
    CLS_RES=$(grep "Resolution.*FSC" "refine_cls${CLS_NUM}.log" 2>/dev/null | tail -1 || true)
    echo ""
    echo "  Class $CLS_NUM: $N_PTCLS particles"
    echo "    Map:        $FINAL_CLS"
    echo "    Resolution: ${CLS_RES:-(see refine_cls${CLS_NUM}.log)}"
    echo "    FSC file:   ${CLS_PATH}/fsc_masked_$(printf "%02d" "${NITER_PERCLASS}").txt"
done
echo ""
echo "Visualization:"
echo "  PCA scatter:    $SPTCLS/pca_scatter.png"
echo "  Class slices:   $SPTCLS/class_averages.png"
for CLS_LST in "$SPTCLS"/ptcls_cls*.lst; do
    CLS_NUM=$(basename "$CLS_LST" | sed 's/ptcls_cls\([0-9]*\)\.lst/\1/')
    CLS_PATH="spt_cls${CLS_NUM}"
    FINAL_CLS="${CLS_PATH}/threed_$(printf "%02d" "${NITER_PERCLASS}").hdf"
    [ -f "$FINAL_CLS" ] && echo "  Class $CLS_NUM 3D: e2display.py $FINAL_CLS"
done
echo ""
echo "Next steps:"
echo "  - Check FSC curves in each spt_cls*/fsc_masked_*.txt"
echo "  - If classes still look similar, re-run PCA with 'r 80' or 'b 16'"
echo "  - If pili show periodic density, investigate helical symmetry (see plan.md)"
