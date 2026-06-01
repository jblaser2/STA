#!/usr/bin/env bash
## runPostClassification.sh
# Run AFTER runClassification.sh completes successfully.
#
# Phase A: PCA scatter plots (Python/matplotlib)
#   Reads eigenfac.star and motl_classified.star; saves PNGs to pca_project/plots/.
#
# Phase B: Per-class averages (ali_multiclass, no angular search)
#   Seeds one dummy reference per class/halfset from the final consensus,
#   then runs STOPGAP to average each class separately.
#   Outputs: pca_project/ref/ref_multiclass_2_{1..N_CLASSES}.mrc

#SBATCH --job-name=stopgap_postclassify
#SBATCH --ntasks=32                         # must match n_cores below
#SBATCH --cpus-per-task=1
#SBATCH --mem-per-cpu=10G
#SBATCH --time=1:00:00
#SBATCH --output=logs/postclassify_%j.log
#SBATCH --error=logs/postclassify_%j.err

set -e
set -o nounset
mkdir -p logs

log() { echo "[$(date '+%H:%M:%S')] $*"; }

# ---- USER CONFIGURATION ----------------------------------------------------
export STOPGAPHOME=/home/ejl62/summerResearch/STOPGAP/exec
SCRIPT_DIR=/home/ejl62/summerResearch/STOPGAP

SUBTOMO_ROOT='/home/ejl62/nobackup/autodelete/stopgapClassification/subtomo_project'
PCA_ROOT='/home/ejl62/nobackup/autodelete/stopgapClassification/pca_project'

n_cores=32       # must match #SBATCH --ntasks
copy_local=1

# Must match the values used in runClassification.sh
FINAL_ITER=10    # motl and ref index produced by Phase 1 (startidx=1 + 9 iters)
N_CLASSES=3
# ---------------------------------------------------------------------------

source "${STOPGAPHOME}/lib/stopgap_config_slurm.sh"

watcher="${STOPGAPHOME}/bin/stopgap_watcher.sh"
parser="${STOPGAPHOME}/bin/stopgap_parser.sh"
stopgap="${STOPGAPHOME}/bin/stopgap_mpi_slurm.sh"

# ---- ACTIVATE CONDA --------------------------------------------------------
# SLURM does not source .bashrc, so conda must be initialised explicitly.
source "${HOME}/miniconda3/etc/profile.d/conda.sh" 2>/dev/null \
    || source "${HOME}/.conda/etc/profile.d/conda.sh" 2>/dev/null \
    || { log "ERROR: conda init script not found under ~/miniconda3 or ~/.conda"; exit 1; }
conda activate stopgap
log "Active Python: $(python3 --version)  |  env: $(conda info --envs | grep '*' | awk '{print $1}')"

# ============================================================================
log "=== PHASE A: PCA scatter plots ==="
# ============================================================================

python3 "${SCRIPT_DIR}/plotPCA.py" \
    "${PCA_ROOT}/pca/eigenfac.star" \
    "${PCA_ROOT}/lists/motl_classified.star" \
    "${PCA_ROOT}/plots"

log "Plots saved to ${PCA_ROOT}/plots/"

# ============================================================================
log "=== PHASE B: Setup for per-class averaging ==="
# ============================================================================

# The ccmask is required for peak finding even with angiter=0 (see research.md).
if [ ! -f "${PCA_ROOT}/masks/ccmask.mrc" ]; then
    log "Copying ccmask.mrc to pca_project/masks/"
    cp "${SUBTOMO_ROOT}/masks/ccmask.mrc" "${PCA_ROOT}/masks/ccmask.mrc"
fi

# STOPGAP's ali_multiclass auto-generates a reflist from ref_name='ref_multiclass'
# and expects one reference per class per halfset at the starting iteration:
#   ref/ref_multiclass_{A,B}_1_{class}.mrc
# Seed these from the final consensus halfset references produced by Phase 1.
log "Seeding per-class references from consensus ref_class1_{A,B}_${FINAL_ITER}.mrc..."
mkdir -p "${PCA_ROOT}/ref"
for class in $(seq 1 "${N_CLASSES}"); do
    for halfset in A B; do
        src="${SUBTOMO_ROOT}/ref/ref_class1_${halfset}_${FINAL_ITER}.mrc"
        dst="${PCA_ROOT}/ref/ref_multiclass_${halfset}_1_${class}.mrc"
        if [ ! -f "${src}" ]; then
            log "ERROR: Source reference not found: ${src}"
            log "       Ensure runClassification.sh Phase 1 completed all ${FINAL_ITER} iterations."
            exit 1
        fi
        cp "${src}" "${dst}"
    done
done
log "Seed references created (${N_CLASSES} classes × 2 halfsets)."

# Pre-create directories to avoid race conditions on first run.
mkdir -p "${PCA_ROOT}/comm" "${PCA_ROOT}/temp" "${PCA_ROOT}/meta" \
         "${PCA_ROOT}/fsc"  "${PCA_ROOT}/params"

# ============================================================================
log "=== PHASE B: Generate multiclass parameter file ==="
# ============================================================================

# Start fresh — the parser appends to existing files, so remove any stale copy.
rm -f "${PCA_ROOT}/params/multiclass_param.star"

# Rules (from research.md):
#   - *_name params must NOT include their directory prefix (STOPGAP prepends it)
#   - rootdir MUST have a trailing slash
eval "${parser}" subtomo \
    param_name params/multiclass_param.star \
    rootdir "${PCA_ROOT}/" \
    tempdir none commdir none rawdir none refdir none \
    maskdir none listdir none fscdir none subtomodir none metadir none \
    subtomo_mode ali_multiclass \
    startidx 1 iterations 1 \
    motl_name motl_classified \
    wedgelist_name wedgelist.star \
    ref_name ref_multiclass \
    subtomo_name subtomo \
    mask_name pca_mask.mrc \
    ccmask_name ccmask.mrc \
    binning 1 \
    angincr 1 angiter 0 \
    phi_angincr 10 phi_angiter 0 \
    search_mode hc search_type cone cone_search_type complete \
    euler_axes zxy \
    euler_1_incr 1 euler_1_iter 1 \
    euler_2_incr 1 euler_2_iter 1 \
    euler_3_incr 1 euler_3_iter 1 \
    apply_laplacian 0 scoring_fcn flcf \
    lp_rad 40 lp_sigma 3 hp_rad 1 hp_sigma 2 \
    calc_exp 0 calc_ctf 0 \
    cos_weight 0 score_weight 0.01 \
    symmetry C1 score_thresh 0 subset 100 \
    avg_mode full ignore_halfsets 0 \
    temperature 0 rot_mode linear fthresh 800 \
    ali_reffilter_name none ali_particlefilter_name none \
    avg_reffilter_name none avg_particlefilter_name none \
    reffiltertype none particlefiltertype none \
    specdir none ps_name none amp_name none specmask_name none

log "Parameter file written: ${PCA_ROOT}/params/multiclass_param.star"

# ============================================================================
log "=== PHASE B: Per-class averaging (ali_multiclass) ==="
log "    Averaging ${N_CLASSES} classes with no angular search (angiter=0)."
log "    Progress: ls ${PCA_ROOT}/ref/ref_multiclass_*"
# ============================================================================

${watcher} "${PCA_ROOT}" "params/multiclass_param.star" ${n_cores} slurm \
    "srun ${stopgap} ${PCA_ROOT} params/multiclass_param.star ${n_cores} ${copy_local} slurm"

# ============================================================================
log "=== Post-classification pipeline complete ==="
# ============================================================================
log "PCA scatter plots:     ${PCA_ROOT}/plots/"
log "Per-class averages (iteration index 2, merged halfsets):"
for class in $(seq 1 "${N_CLASSES}"); do
    log "  Class ${class}: ${PCA_ROOT}/ref/ref_multiclass_2_${class}.mrc"
done
log "Halfset-specific files follow the same pattern with _A_ or _B_ before the iteration."
log "View in ChimeraX: open ${PCA_ROOT}/ref/ref_multiclass_2_*.mrc"
