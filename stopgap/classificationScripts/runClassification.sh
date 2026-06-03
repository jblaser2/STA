#!/usr/bin/env bash
## runClassification.sh
# Single SLURM job that runs the full classification pipeline:
#   1. Subtomogram alignment (6 iterations, 3 angular-search blocks)
#   2. PCA (rot_vol → calc_covar → calc_eigenval → calc_eigenvec)
#   3. k-means clustering and class-label assignment
#
# Prerequisites (must be done before submitting this job):
#   - createStopgapInputs.m has been run in MATLAB
#   - subtomoParams.sh has been run to generate subtomo_param.star
#   - STOPGAP compiled against r2023b MCR and STOPGAPHOME is set
#
# How the watcher works inside a SLURM job:
#   The watcher (stopgap_watcher) runs as the main job process.
#   Each iteration it calls `srun stopgap_mpi_slurm.sh` to launch n_cores
#   MPI workers as a SLURM job step within this allocation, waits for all
#   filesystem completion flags (comm/sg_ali_*, comm/sg_p_avg_*, etc.),
#   runs final assembly, then advances to the next task block.
#   This is fully supported by SLURM and requires no nested sbatch calls.

#SBATCH --job-name=stopgap_classify
#SBATCH --ntasks=32                        # must match n_cores below
#SBATCH --cpus-per-task=1
#SBATCH --mem-per-cpu=10G
#SBATCH --time=2-0:00:00                    # adjust; subtomo dominates runtime
#SBATCH --output=logs/classify_%j.log
#SBATCH --error=logs/classify_%j.err

set -e
set -o nounset
mkdir -p logs

log() { echo "[$(date '+%H:%M:%S')] $*"; }

# Report the failing command and line on any unexpected error so the cause
# lands in logs/classify_%j.err instead of the job dying silently.
trap 'rc=$?; echo "ACHTUNG: runClassification.sh failed at line ${LINENO} (exit ${rc}): ${BASH_COMMAND}" >&2' ERR

# ---- USER CONFIGURATION ----------------------------------------------------
export STOPGAPHOME=/home/ejl62/summerResearch/STOPGAP/exec
MATLAB_TOOLBOX=/home/ejl62/summerResearch/STOPGAP/sg_toolbox  # for clustering step

SUBTOMO_ROOT='/home/ejl62/nobackup/autodelete/stopgapClassification/subtomo_project'
PCA_ROOT='/home/ejl62/nobackup/autodelete/stopgapClassification/pca_project'

n_cores=32        # must match #SBATCH --ntasks
copy_local=1      # /tmp is local LVM (209 GB) on BYU HPC nodes — not NFS

# Final iteration number: must match subtomoParams.sh schedule.
# 6 iterations (2 per block, the tuned schedule) → output motl is motl_7.star.
# If you change the iteration count in subtomoParams.sh, update this to
# (total_iterations + 1).
FINAL_ITER=7
# ---------------------------------------------------------------------------

# Source MCR libraries
source "${STOPGAPHOME}/lib/stopgap_config_slurm.sh"

watcher="${STOPGAPHOME}/bin/stopgap_watcher.sh"
parser="${STOPGAPHOME}/bin/stopgap_parser.sh"
stopgap="${STOPGAPHOME}/bin/stopgap_mpi_slurm.sh"

# run_watcher_guarded <project_root> <param_file>
# Runs the watcher with a crash sentinel. A single MPI worker crash writes a
# crash_<n> marker into the project dir; the watcher only treats this as fatal
# once EVERY core has crashed (and even then only if recompiled with the
# updated check_crashes.m), otherwise it polls forever for completion flags
# that never arrive and the job hangs until wall-time — a silent failure.
# This sentinel detects ANY crash marker within ~20 s, prints it to the job
# log, kills the watcher, and exits non-zero so the failure is loud and
# immediate. The 20 s poll adds negligible overhead.
run_watcher_guarded() {
    local root="$1"
    local paramfile="$2"

    # Clear stale crash markers so we only react to crashes from THIS run.
    rm -f "${root}"/crash_* 2>/dev/null || true

    ${watcher} "${root}" "${paramfile}" ${n_cores} slurm \
        "srun ${stopgap} ${root} ${paramfile} ${n_cores} ${copy_local} slurm" &
    local wpid=$!

    while kill -0 "${wpid}" 2>/dev/null; do
        sleep 20
        if compgen -G "${root}/crash_*" > /dev/null; then
            log "ACHTUNG: worker crash detected — aborting job (crash marker below)"
            cat "${root}"/crash_* >&2
            kill -TERM "${wpid}" 2>/dev/null || true
            sleep 5
            kill -KILL "${wpid}" 2>/dev/null || true
            wait "${wpid}" 2>/dev/null || true
            log "Aborted: a STOPGAP MPI worker crashed. Inspect ${root}/crash_* and the srun output above."
            exit 1
        fi
    done

    # Propagate the watcher exit code; set -e aborts the job if it is non-zero.
    wait "${wpid}"
}

# ---- PRE-FLIGHT CHECKS -----------------------------------------------------
# Fail loudly and early (before consuming wall-time) if a required input is
# missing — a common cause of opaque mid-run failures.
preflight() {
    local missing=0
    for f in "$@"; do
        if [ ! -e "${f}" ]; then
            log "ACHTUNG: required input missing: ${f}"
            missing=1
        fi
    done
    [ "${missing}" -eq 0 ] || { log "Aborting: missing required inputs (see above)."; exit 1; }
}

preflight \
    "${SUBTOMO_ROOT}/params/subtomo_param.star" \
    "${SUBTOMO_ROOT}/lists/motl_1.star" \
    "${SUBTOMO_ROOT}/lists/wedgelist.star" \
    "${SUBTOMO_ROOT}/ref/ref_class1_1.mrc" \
    "${SUBTOMO_ROOT}/ref/ref_class1_A_1.mrc" \
    "${SUBTOMO_ROOT}/ref/ref_class1_B_1.mrc" \
    "${SUBTOMO_ROOT}/masks/ali_mask.mrc" \
    "${SUBTOMO_ROOT}/masks/ccmask.mrc" \
    "${SUBTOMO_ROOT}/subtomograms"

# ============================================================================
log "=== PHASE 1: Subtomogram alignment (6 iterations) ==="
log "Iteration progress: ls ${SUBTOMO_ROOT}/lists/motl_*.star"
# ============================================================================
# The watcher reads subtomo_param.star and runs all 6 task blocks in sequence.
# Each task block: align → average → FSC. Completion is signalled via
# filesystem flags in subtomo_project/comm/.

run_watcher_guarded "${SUBTOMO_ROOT}" "params/subtomo_param.star"

log "Phase 1 complete. Final motl: motl_${FINAL_ITER}.star"

# Verify the expected final motl actually exists; if not, surface diagnostics
# rather than letting the PCA copy step fail with an opaque error.
if [ ! -f "${SUBTOMO_ROOT}/lists/motl_${FINAL_ITER}.star" ]; then
    log "ACHTUNG: expected ${SUBTOMO_ROOT}/lists/motl_${FINAL_ITER}.star not found after Phase 1!"
    if compgen -G "${SUBTOMO_ROOT}/crash_*" > /dev/null; then cat "${SUBTOMO_ROOT}"/crash_* >&2; fi
    exit 1
fi

# Surface any non-fatal averaging warnings (Fourier dynamic-range, empty class)
# into the job log so they are not buried in the project ref/ directory.
if compgen -G "${SUBTOMO_ROOT}/ref/warning_*.txt" > /dev/null; then
    log "Non-fatal warnings were written during alignment:"
    for w in "${SUBTOMO_ROOT}"/ref/warning_*.txt; do
        echo "  --- ${w} ---" >&2
        sed 's/^/    /' "${w}" >&2
    done
fi

# ============================================================================
log "=== Setting up PCA project ==="
# ============================================================================
# Copy final outputs from subtomo project into PCA project.
mkdir -p "${PCA_ROOT}/lists" "${PCA_ROOT}/ref" "${PCA_ROOT}/masks"

log "Copying motl_${FINAL_ITER}.star to pca_project/lists/"
cp "${SUBTOMO_ROOT}/lists/motl_${FINAL_ITER}.star"       "${PCA_ROOT}/lists/"
log "Copying wedgelist.star to pca_project/lists/"
cp "${SUBTOMO_ROOT}/lists/wedgelist.star"                 "${PCA_ROOT}/lists/"
log "Copying ref_class1_${FINAL_ITER}.mrc to pca_project/ref/"
cp "${SUBTOMO_ROOT}/ref/ref_class1_${FINAL_ITER}.mrc"    "${PCA_ROOT}/ref/"
log "Copying ali_mask.mrc to pca_project/masks/pca_mask.mrc"
cp "${SUBTOMO_ROOT}/masks/ali_mask.mrc"                   "${PCA_ROOT}/masks/pca_mask.mrc"

# Subtomograms: symlink to avoid duplicating 672 files
if [ ! -d "${PCA_ROOT}/subtomograms" ]; then
    log "Symlinking subtomograms directory"
    ln -s "${SUBTOMO_ROOT}/subtomograms" "${PCA_ROOT}/subtomograms"
fi
log "PCA project setup complete."

# ============================================================================
log "=== PHASE 2: PCA (4 tasks) ==="
# ============================================================================
# PCA param files are NOT appended — each call to the parser overwrites the
# previous file. We run each task separately: parse → watcher → parse → ...

pca_common_args="pca \
    param_name params/pca_param.star rootdir ${PCA_ROOT} \
    tempdir none commdir none rawdir none refdir none \
    maskdir none listdir none subtomodir none rvoldir none \
    pcadir none metadir none \
    iteration ${FINAL_ITER} \
    motl_name motl \
    wedgelist_name lists/wedgelist.star \
    binning 1 \
    ref_name ref_class1 \
    mask_name masks/pca_mask.mrc \
    subtomo_name subtomo \
    rvol_name rvol \
    rwei_name rwei \
    filtlist_name lists/filter_list.star \
    data_type awpd \
    ccmat_name ccmatrix \
    covar_name covar \
    n_eigs 10 \
    eigenvol_name eigenvol \
    eigenfac_name eigenfac \
    eigenval_name eigenval \
    apply_laplacian 0 \
    scoring_fcn pearson \
    symmetry c1 \
    fthresh 300"

run_pca_task() {
    local task=$1
    log "PCA task start: ${task}"
    eval "${parser} ${pca_common_args} pca_task ${task}"
    run_watcher_guarded "${PCA_ROOT}" "params/pca_param.star"
    log "PCA task done: ${task}"
}

run_pca_task rot_vol       # pre-rotate all particles into reference frame
run_pca_task calc_covar    # build covariance matrix (O(N²), fast for 672 particles)
run_pca_task calc_eigenval # compute eigenvalues
run_pca_task calc_eigenvec # compute eigenvectors and per-particle factor scores

# ============================================================================
log "=== PHASE 3: Clustering (k-means, n_classes=${N_CLASSES:-3}) ==="
# ============================================================================
# Run k-means in MATLAB using the compiled toolbox (no interactive MATLAB needed).
# The toolbox binary exposes sg_pca_kmeans_cluster for command-line use.
# Alternatively, run the MATLAB script below if MATLAB is available on compute nodes.

N_CLASSES=3
EIGENFAC="${PCA_ROOT}/pca/eigenfac.star"
MOTL_IN="${PCA_ROOT}/lists/motl_${FINAL_ITER}.star"
MOTL_OUT="${PCA_ROOT}/lists/motl_classified.star"

module load matlab/r2023b 2>/dev/null || true
log "Starting MATLAB k-means (${N_CLASSES} classes, 10 replicates)..."

matlab -nodisplay -nosplash -r "
    addpath(genpath('${MATLAB_TOOLBOX}'));
    cd('${PCA_ROOT}');

    n_classes    = ${N_CLASSES};
    eigenfac_file = '${EIGENFAC}';
    motl_file     = '${MOTL_IN}';
    out_motl_file = '${MOTL_OUT}';

    % Load eigenfactors (N x n_eigs table from STAR file)
    ef_star  = stopgap_star_read(eigenfac_file);
    fields   = fieldnames(ef_star);
    n_eigs   = numel(fields);
    n_part   = numel(ef_star.(fields{1}));
    scores   = zeros(n_part, n_eigs);
    for f = 1:n_eigs
        scores(:, f) = ef_star.(fields{f});
    end

    % k-means on first 4 components (edit n_components as needed)
    n_components = min(4, n_eigs);
    rng(42);
    class_labels = kmeans(scores(:,1:n_components), n_classes, ...
                          'Replicates', 10, 'MaxIter', 500);

    % Write class labels into motivelist
    motl = sg_motl_read(motl_file);
    motl.class = class_labels;
    sg_motl_write(out_motl_file, motl);

    fprintf('Classification complete. Classes written to %s\n', out_motl_file);

    % Print class counts
    for c = 1:n_classes
        fprintf('  Class %d: %d particles\n', c, sum(class_labels == c));
    end

    exit;
"

log "=== Classification pipeline complete ==="
log "Classified motivelist: ${MOTL_OUT}"
log "To generate per-class averages: subtomo_mode=ali_multiclass, iterations=1, angincr=1, angiter=0"
