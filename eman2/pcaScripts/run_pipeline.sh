#!/bin/bash
# EMAN2 subtomogram PCA classification pipeline -- NO ALIGNMENT variant.
#
# The subvolumes in this dataset are already aligned at Euler angles (0,0,0).
# We therefore DO NOT run any subtomogram orientation search (e2spt_refine.py /
# e2spt_align.py). Instead, particles are averaged in their given orientation
# (identity xform) with missing-wedge-aware averaging, and PCA classification
# applies those same identity transforms.
#
# Usage: ./run_pipeline.sh
set -euo pipefail

CONDA_BASE="/home/ejl62/miniforge3"
PROJECT_DIR="/home/ejl62/src/eman2_project"

# ---- Parameters (edit these before running) ----
NCLASS=2              # number of K-Means clusters
NBASIS=12             # PCA basis vectors (loosened from 8 to capture subtler variance)
MAXRES=60             # low-pass before PCA in Å (matches actual signal range)
SYM=c1                # symmetry
THREADS=24            # CPU threads for averaging/post-processing
CLEAN=1               # 1 = --clean removes PCA outliers before K-Means
RESTARGET=30          # Å — target resolution passed to e2refine_postprocess
# NOTE: there is no --pkeep here. pkeep culled particles by *alignment score*,
# which no longer exists once we stop aligning. All particles are kept.
# -------------------------------------------------

# Derived paths — do not edit these
CONS_PATH="spt_noalign"          # consensus (no-align) average + mask live here
CONS_ITER=1                      # single pass — no iterations without alignment
CONS_ITER2=$(printf "%02d" "$CONS_ITER")
CONS_PARMS="${CONS_PATH}/particle_parms_${CONS_ITER2}.json"
CONS_MAP="${CONS_PATH}/threed_${CONS_ITER2}.hdf"
CONS_MASK="${CONS_PATH}/mask_tight.hdf"

log() { echo "[$(date '+%H:%M:%S')] $*"; }

# ---- Activate eman2 conda environment ----
source "$CONDA_BASE/etc/profile.d/conda.sh"
conda activate eman2
export PATH="$CONDA_BASE/envs/eman2/bin:$PATH"

cd "$PROJECT_DIR"
log "Working in $PROJECT_DIR"
log "EMAN2 Python: $(which python)"

# ---- noalign_average: build threed + even/odd + mask for a set of particles ----
# Averages particles at their given (identity) orientation -- NO alignment search.
# Args: $1 = path (spt dir), $2 = iter (int), $3 = lst file (only needed when the
#       particle_parms json does not already exist in the path).
noalign_average() {
    local path="$1" itr="$2" lst="${3:-}"
    local itr2; itr2=$(printf "%02d" "$itr")
    local parms="${path}/particle_parms_${itr2}.json"
    local even="${path}/threed_${itr2}_even.hdf"
    local odd="${path}/threed_${itr2}_odd.hdf"
    local comb="${path}/threed_${itr2}.hdf"

    mkdir -p "$path"

    # 1. Identity orientations (only if not already provided, e.g. by pcasplit).
    if [ ! -f "$parms" ]; then
        [ -n "$lst" ] || { echo "ERROR: noalign_average needs an lst to build $parms"; exit 1; }
        log "  Writing identity particle_parms → $parms"
        python make_identity_parms.py "$lst" "$parms"
    fi

    # 2. Missing-wedge-aware average of even/odd halves (no orientation search).
    log "  Averaging (mean.tomo, identity orientation) → $comb"
    { e2spt_average.py \
        --path "$path" \
        --iter "$itr" \
        --sym "$SYM" \
        --keep 1.0 \
        --threads "$THREADS" \
        --skippostp \
        --verbose 1; } 255>&-

    # 3. Post-process: gold-standard masked FSC, mask.hdf + mask_tight.hdf, filter.
    log "  Post-processing (FSC, masks, Wiener) for $path iter $itr2"
    { e2refine_postprocess.py \
        --even "$even" \
        --odd "$odd" \
        --output "$comb" \
        --iter "$itr" \
        --tomo \
        --mass -1 \
        --threads "$THREADS" \
        --restarget "$RESTARGET" \
        --sym "$SYM" \
        --align; } 255>&-
}

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

for f in particles.hdf ptcls.lst; do
    [ -f "$f" ] || { echo "ERROR: $f not found after ingestion"; exit 1; }
done

# ---- Step 3: Consensus average WITHOUT alignment ----
# Particles are already at Euler (0,0,0); we just co-add them (missing-wedge
# aware) to build the reference map + tight mask that PCA classification needs.
# No seed refinement and no full refinement — there is nothing to align.
if [ -f "$CONS_MAP" ] && [ -f "$CONS_MASK" ] && [ -f "$CONS_PARMS" ]; then
    log "Step 3: Consensus average exists ($CONS_MAP) — skipping."
else
    log "Step 3: Building consensus average (no alignment) in $CONS_PATH/..."
    noalign_average "$CONS_PATH" "$CONS_ITER" ptcls.lst
fi

for f in "$CONS_MAP" "$CONS_MASK" "$CONS_PARMS"; do
    [ -f "$f" ] || { echo "ERROR: consensus build failed — $f missing"; exit 1; }
done

CONS_RES=$(python3 -c "
import numpy as np
try:
    fsc=np.loadtxt('${CONS_PATH}/fsc_masked_${CONS_ITER2}.txt')
    fi=fsc[:,1]<0.143
    print('{:.1f} A (FSC=0.143)'.format(1./fsc[fi,0][0]) if np.any(fi) else 'n/a')
except Exception as e:
    print('n/a')
")
log "Consensus resolution: $CONS_RES"

# ---- Step 4: PCA classification (interactive loop) ----
SPTCLS=""

while true; do
    CLEAN_FLAG=""
    [ "$CLEAN" -eq 1 ] && CLEAN_FLAG="--clean"

    log "Step 4: PCA classification (nclass=$NCLASS, nbasis=$NBASIS, maxres=$MAXRES Å, clean=$CLEAN)..."
    log "        Applying identity transforms from $CONS_PARMS (no re-alignment)."
    { e2spt_pcasplit.py \
        --path "$CONS_PATH" \
        --iter "$CONS_ITER" \
        --nclass "$NCLASS" \
        --nbasis "$NBASIS" \
        --maxres "$MAXRES" \
        --sym "$SYM" \
        --mask "$CONS_MASK" \
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
    echo "  [Enter]   Accept — proceed to per-class averaging"
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

# ---- Step 6: Per-class average WITHOUT alignment ----
# pcasplit already wrote per-class particle_parms_NN.json (carrying the same
# identity transforms) and ptcls_clsNN.lst into $SPTCLS. We just re-average each
# class with even/odd halves + post-processing to get a gold-standard FSC and a
# per-class mask. Still no orientation search.
log "Step 6: Per-class averaging (no alignment, restarget=${RESTARGET} Å)..."
echo ""

for CLS_LST in "$SPTCLS"/ptcls_cls*.lst; do
    CLS_NUM=$(basename "$CLS_LST" | sed 's/ptcls_cls\([0-9]*\)\.lst/\1/')
    CLS_ITR=$((10#$CLS_NUM))
    CLS_ITR2=$(printf "%02d" "$CLS_ITR")
    FINAL_CLS="$SPTCLS/threed_${CLS_ITR2}_even.hdf"   # even half = sign that post-proc ran
    N_PTCLS=$(wc -l < "$CLS_LST")

    if [ -f "$FINAL_CLS" ] && [ -f "$SPTCLS/fsc_masked_${CLS_ITR2}.txt" ]; then
        log "  Class $CLS_NUM: already averaged — skipping."
        continue
    fi

    log "  Class $CLS_NUM: Averaging $N_PTCLS particles (identity orientation)..."
    # particle_parms_${CLS_ITR2}.json already exists in $SPTCLS (written by pcasplit),
    # so noalign_average reuses it rather than rebuilding identity parms.
    noalign_average "$SPTCLS" "$CLS_ITR"

    # e2refine_postprocess writes mask.hdf / mask_tight.hdf with fixed names, so
    # preserve this class's masks before the next class overwrites them.
    [ -f "$SPTCLS/mask.hdf" ]       && cp -f "$SPTCLS/mask.hdf"       "$SPTCLS/mask_cls${CLS_ITR2}.hdf"
    [ -f "$SPTCLS/mask_tight.hdf" ] && cp -f "$SPTCLS/mask_tight.hdf" "$SPTCLS/mask_tight_cls${CLS_ITR2}.hdf"
    log "  Class $CLS_NUM done."
done

# ---- Final summary ----
echo ""
log "=== Pipeline complete (NO subtomogram alignment performed) ==="
echo ""
echo "Consensus average:  $CONS_PATH/  (identity orientation, no alignment)"
echo "  Resolution: $CONS_RES"
echo ""
echo "Classification:     $SPTCLS/"
echo ""
echo "Per-class results:"
for CLS_LST in "$SPTCLS"/ptcls_cls*.lst; do
    CLS_NUM=$(basename "$CLS_LST" | sed 's/ptcls_cls\([0-9]*\)\.lst/\1/')
    CLS_ITR2=$(printf "%02d" "$((10#$CLS_NUM))")
    N_PTCLS=$(wc -l < "$CLS_LST")
    CLS_RES=$(python3 -c "
import numpy as np
try:
    fsc=np.loadtxt('$SPTCLS/fsc_masked_${CLS_ITR2}.txt')
    fi=fsc[:,1]<0.143
    print('{:.1f} A (FSC=0.143)'.format(1./fsc[fi,0][0]) if np.any(fi) else 'n/a')
except Exception:
    print('(see $SPTCLS/fsc_masked_${CLS_ITR2}.txt)')
")
    echo ""
    echo "  Class $CLS_NUM: $N_PTCLS particles"
    echo "    Map:        $SPTCLS/threed_${CLS_ITR2}.hdf"
    echo "    Resolution: $CLS_RES"
    echo "    FSC file:   $SPTCLS/fsc_masked_${CLS_ITR2}.txt"
done
echo ""
echo "Visualization:"
echo "  PCA scatter:    $SPTCLS/pca_scatter.png"
echo "  Class slices:   $SPTCLS/class_averages.png"
for CLS_LST in "$SPTCLS"/ptcls_cls*.lst; do
    CLS_NUM=$(basename "$CLS_LST" | sed 's/ptcls_cls\([0-9]*\)\.lst/\1/')
    CLS_ITR2=$(printf "%02d" "$((10#$CLS_NUM))")
    [ -f "$SPTCLS/threed_${CLS_ITR2}.hdf" ] && echo "  Class $CLS_NUM 3D: e2display.py $SPTCLS/threed_${CLS_ITR2}.hdf"
done
echo ""
echo "Next steps:"
echo "  - Check FSC curves in $SPTCLS/fsc_masked_*.txt"
echo "  - If classes still look similar, re-run PCA with 'r 80' or 'b 16'"
