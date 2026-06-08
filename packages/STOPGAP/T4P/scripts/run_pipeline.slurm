#!/bin/bash
#SBATCH --job-name=pili_class
#SBATCH --nodes=1
#SBATCH --ntasks=64                    # alignment/PCA/averaging cores
#SBATCH --cpus-per-task=1              # STOPGAP ranks are single-threaded
#SBATCH --mem-per-cpu=4G
#SBATCH --time=12:00:00
#SBATCH -o pili_class_%j.log
#SBATCH -e pili_class_%j.err
set -Eeuo pipefail

############################ USER CONFIG ############################
SG=/home/ejl62/summerResearch/STA/STOPGAP
export STOPGAPHOME=$SG/exec
ROOT=/home/ejl62/Pili_class                      # project working dir
PARTICLES=/home/ejl62/groups/grp_tomo/Pili_PCA/particles
MINT=-60; MAXT=60; STEP=3                         # <-- set real tilt range values
DO_ALIGN=0                                         # 0 = skip alignment; particles are prealigned at (0,0,0)
DO_MRA=1                                           # 1 = also run MRA + cross-method compare
KS=(2 3 4)                                         # k values for clustering
PX=AUTO                                            # 'AUTO' = read from header; or set Å/px
# LP_RAD below is set to 17 (placeholder). Derive the real value once pixel
# size is confirmed: lp_rad ~ box/2 * (px / target_res_A), or use Nyquist
# e.g. for px=5.4A, box=80, 17 Fourier px ≈ 19A resolution cutoff.
NC=$SLURM_NTASKS
####################################################################

module load matlab/r2023b
# MATLAB path added to every matlab -batch call
MLP="addpath(genpath('$SG/src'));addpath(genpath('$SG/sg_toolbox'));addpath('$SG/scripts');"

mkdir -p "$ROOT" "$ROOT/logs"
cd "$ROOT"

# Parsers read back existing param files via [rootdir,paramfilename] with NO
# separator (sg_read_subtomo_param / sg_read_pca_param), while the exist() check
# uses a slash. Pass rootdir WITH a trailing slash so the append-read path
# resolves to the right file instead of erroring.
ROOTS="${ROOT%/}/"

# -----------------------------------------------------------------------
# Fail-loud stage wrapper: checks exit code, STOPGAP fatal markers,
# crash files, and (optionally) expected output existence.
# Cost: a handful of grep/test calls between multi-minute compute stages.
# -----------------------------------------------------------------------
trap 'echo "ACHTUNG!!! pipeline aborted at line $LINENO: $BASH_COMMAND" >&2' ERR

stage() {   # stage <name> <command...>
    local name="$1"; shift
    echo "=== [$(date +%T)] START $name ==="
    rm -f "$ROOT"/crash_* 2>/dev/null || true
    set +e
    ( "$@" ) 2>&1 | tee "$ROOT/logs/$name.log"
    local rc=${PIPESTATUS[0]}
    set -e
    if [ $rc -ne 0 ]; then
        echo "ACHTUNG!!! stage '$name' exited with code $rc"; exit $rc
    fi
    local PAT='ACHTUNG!!!|Segmentation fault|Killed|Out of memory|Cannot allocate'
    # STOPGAP prints benign MATLAB warnings that contain "ACHTUNG!!!" (e.g.
    # 'Warning: ACHTUNG!!! "fieldtypes" will be used...' from stopgap_star_read
    # during normal averaging). Genuine fatals are never prefixed with
    # "Warning:", so drop those lines before deciding whether to abort.
    local hits
    hits=$(grep -E "$PAT" "$ROOT/logs/$name.log" | grep -vE 'Warning:.*ACHTUNG' || true)
    if [ -n "$hits" ]; then
        echo "ACHTUNG!!! stage '$name' logged a fatal marker:"
        printf '%s\n' "$hits" | head -5
        exit 1
    fi
    if ls "$ROOT"/crash_* >/dev/null 2>&1; then
        echo "ACHTUNG!!! crash file(s) found after '$name'"; exit 1
    fi
    echo "=== [$(date +%T)] DONE  $name ==="
}

assert_exists() { [ -s "$1" ] || { echo "ACHTUNG!!! expected output missing/empty: $1"; exit 1; }; }

# Run matlab -batch with the STOPGAP + scripts paths
mlbatch() { matlab -nodisplay -nosplash -batch "$MLP $1"; }

# Direct srun over a whole param file (no watcher; worker loops over all rows)
sg_run() { srun --ntasks=$NC --cpus-per-task=1 \
    $STOPGAPHOME/bin/stopgap_mpi_slurm.sh "$ROOT" "$1" $NC 0 slurm; }

# Shared subtomo parser args for 'none' directories and external filters
# (all 'none' means STOPGAP uses its default relative paths)
DIRNONE=(tempdir none commdir none rawdir none refdir none maskdir none \
         listdir none fscdir none subtomodir none metadir none)
FILTNONE=(ali_reffilter_name none ali_particlefilter_name none \
          avg_reffilter_name none avg_particlefilter_name none \
          reffiltertype none particlefiltertype none \
          specdir none ps_name none amp_name none specmask_name none)
EULER=(euler_axes zxy euler_1_incr 1 euler_1_iter 1 \
       euler_2_incr 1 euler_2_iter 3 euler_3_incr 1 euler_3_iter 1)
# Common in-plane-only search params (angiter=0 -> single cone orientation -> Z fixed)
CONE_INPLANE=(search_mode hc search_type cone \
              angincr 4 angiter 0 phi_angincr 4 phi_angiter 45 \
              cone_search_type coarse apply_laplacian 0 scoring_fcn flcf \
              lp_rad 13.33 lp_sigma 3 hp_rad 1 hp_sigma 2 \
              calc_exp 0 calc_ctf 0 cos_weight 0 score_weight 1 \
              symmetry C1 score_thresh 0 subset 100 avg_mode full \
              ignore_halfsets 0 temperature 0 rot_mode linear fthresh 800)

# Classify-only search params for MRA. Particles are prealigned at (0,0,0), so
# MRA (ali_multiref) should assign classes WITHOUT re-orienting them: same
# scoring/filter settings, but the in-plane phi search disabled (phi_angiter 0;
# angiter is already 0 so theta/psi are fixed too). Derived from CONE_INPLANE so
# there is a single source of truth for the scoring/filter settings, and the
# align path keeps its full phi sweep if DO_ALIGN is ever re-enabled. We rewrite
# the value in place (not append) because the parser uses MATLAB inputParser,
# which errors if a name-value key appears twice.
MRA_INPLANE=("${CONE_INPLANE[@]}")
for i in "${!MRA_INPLANE[@]}"; do
    [ "${MRA_INPLANE[$i]}" = "phi_angiter" ] && MRA_INPLANE[$((i+1))]=0
done

# -----------------------------------------------------------------------
# 0) Initialize STOPGAP folder structure
# -----------------------------------------------------------------------
stage init_folders bash -c "
  bash $STOPGAPHOME/bin/stopgap_initialize_folder.sh pca
  bash $STOPGAPHOME/bin/stopgap_initialize_folder.sh subtomo"

# Clear stale param files from any prior run. The parsers APPEND to an existing
# param file (intentional: the PCA/avg loops build multi-row files across calls),
# so leftover files would otherwise accumulate duplicate rows on a rerun.
rm -f "$ROOT"/params/*.star 2>/dev/null || true

# Clear stale comm/ flags. stopgap_initialize_folder.sh only mkdir's comm/, it
# never clears it, so completion/coordination flags (complete_*, sg_*, node_*,
# ccmatprog_*, sg_pca_ccmatrix_*) survive across runs. A leftover flag can satisfy
# a wait_for_them() count prematurely (the master proceeds on missing/old data) or
# leave file-based coordination half-initialized. Start every run from an empty
# comm/ so all waits are driven only by this run's flags.
rm -f "$ROOT"/comm/* 2>/dev/null || true

# -----------------------------------------------------------------------
# 1) Build inputs, wedgelist, masks+ref, PCA aux files
# -----------------------------------------------------------------------
stage build_inputs  mlbatch "build_inputs('$PARTICLES','$ROOT');"
assert_exists "$ROOT/lists/allmotl_1.star"

stage build_wedge   mlbatch "build_wedgelist('$ROOT',$MINT,$MAXT,$STEP);"
assert_exists "$ROOT/lists/wedgelist.star"

stage build_masks   mlbatch "build_masks_ref('$ROOT');"
assert_exists "$ROOT/ref/ref_1.mrc"
# singleref alignment reads per-halfset references; catch a missing one here
# (cheap) rather than after a full srun allocation in run_align.
assert_exists "$ROOT/ref/ref_A_1.mrc"
assert_exists "$ROOT/ref/ref_B_1.mrc"
assert_exists "$ROOT/masks/mask_align.mrc"

stage build_pca_aux mlbatch "build_pca_aux('$ROOT',13.33,3,1,2);"
assert_exists "$ROOT/lists/filter_list.star"

# -----------------------------------------------------------------------
# 2) (Optional) In-plane alignment: full +-180 deg phi sweep, Z fixed
#    Produces allmotl_3 (2 iterations: 1->2->3) and ref_3.
# -----------------------------------------------------------------------
if [ "$DO_ALIGN" -eq 1 ]; then
    stage parse_align $STOPGAPHOME/bin/stopgap_parser.sh subtomo \
        param_name params/align_param.star \
        rootdir "$ROOTS" "${DIRNONE[@]}" "${FILTNONE[@]}" \
        subtomo_mode ali_singleref startidx 1 iterations 2 binning 1 \
        motl_name allmotl wedgelist_name wedgelist.star \
        ref_name ref subtomo_name subtomo \
        mask_name mask_align.mrc ccmask_name mask_cc.mrc \
        "${EULER[@]}" "${CONE_INPLANE[@]}"

    stage run_align sg_run params/align_param.star
    assert_exists "$ROOT/lists/allmotl_3.star"
    ITER=3
else
    ITER=1
fi

# -----------------------------------------------------------------------
# 3) PCA: rot_vol -> calc_ccmat -> calc_pca_ccmat (3 rows, one srun)
# -----------------------------------------------------------------------
PCA_COMMON=(rootdir "$ROOTS" tempdir none commdir none rawdir none refdir none \
  maskdir none listdir none subtomodir none rvoldir none pcadir none metadir none \
  iteration $ITER motl_name allmotl wedgelist_name wedgelist.star binning 1 \
  ref_name ref mask_name mask_align.mrc subtomo_name subtomo \
  rvol_name rvol rwei_name rwei \
  filtlist_name filter_list.star data_type awpd \
  ccmat_name ccmatrix covar_name covar n_eigs 10 \
  eigenvol_name eigenvol eigenfac_name eigenfac eigenval_name eigenval \
  apply_laplacian 0 symmetry c1 fthresh 300)

for task in rot_vol calc_ccmat calc_pca_ccmat; do
    stage "parse_pca_$task" $STOPGAPHOME/bin/stopgap_parser.sh pca \
        param_name params/pca_param.star pca_task $task "${PCA_COMMON[@]}"
done

stage run_pca sg_run params/pca_param.star
assert_exists "$ROOT/pca/eigenval_1.csv"

# -----------------------------------------------------------------------
# 4) k-means clustering (k=2,3,4) using PCs 1-3 from filter 1
# -----------------------------------------------------------------------
stage kmeans mlbatch \
    "sg_pca_kmeans_cluster_fn('$ROOT','params/pca_param.star',[1 1;1 2;1 3],[${KS[*]}]);"
for k in "${KS[@]}"; do
    assert_exists "$ROOT/lists/allmotl_pca_k${k}_${ITER}.star"
done

# -----------------------------------------------------------------------
# 5) Class averages per k (avg_multiclass; halfsets on -> per-class FSC)
# -----------------------------------------------------------------------
for k in "${KS[@]}"; do
    stage "parse_avg_pca_k$k" $STOPGAPHOME/bin/stopgap_parser.sh subtomo \
        param_name params/avg_pca_param.star \
        rootdir "$ROOTS" "${DIRNONE[@]}" "${FILTNONE[@]}" \
        subtomo_mode avg_multiclass startidx $ITER iterations 1 binning 1 \
        motl_name allmotl_pca_k$k wedgelist_name wedgelist.star \
        ref_name class_pca_k$k subtomo_name subtomo \
        mask_name mask_align.mrc ccmask_name none \
        "${EULER[@]}" \
        calc_exp 0 calc_ctf 0 cos_weight 0 score_weight 1 \
        symmetry C1 score_thresh 0 subset 100 avg_mode full \
        ignore_halfsets 0 temperature 0 rot_mode linear fthresh 800
done

stage run_avg_pca sg_run params/avg_pca_param.star

# -----------------------------------------------------------------------
# 6) Visualize PCA results (scatter + class-average slices)
# -----------------------------------------------------------------------
PX_VAL=$( [ "$PX" = "AUTO" ] && echo 0 || echo "$PX" )
stage viz_pca mlbatch \
    "visualize_results('$ROOT','$ROOT/pca/eigenval_1.csv','lists/allmotl_pca_k%d_%d.star','class_pca',[${KS[*]}],$PX_VAL);"

# -----------------------------------------------------------------------
# 7) (Optional) MRA pipeline + cross-method comparison
# -----------------------------------------------------------------------
if [ "$DO_MRA" -eq 1 ]; then

    # 7a) Seed random class labels for each k
    for k in "${KS[@]}"; do
        stage "seed_mra_k$k" mlbatch \
            "sg_motl_apply_random_classes('$ROOT/lists/allmotl_${ITER}.star',$k,'$ROOT/lists/allmotl_mra_k${k}_${ITER}.star');"
        assert_exists "$ROOT/lists/allmotl_mra_k${k}_${ITER}.star"
    done

    # 7b) Initial references via avg_multiclass on seed motls
    for k in "${KS[@]}"; do
        stage "parse_mraseed_k$k" $STOPGAPHOME/bin/stopgap_parser.sh subtomo \
            param_name params/mraseed_param.star \
            rootdir "$ROOTS" "${DIRNONE[@]}" "${FILTNONE[@]}" \
            subtomo_mode avg_multiclass startidx $ITER iterations 1 binning 1 \
            motl_name allmotl_mra_k$k wedgelist_name wedgelist.star \
            ref_name ref_mra_k$k subtomo_name subtomo \
            mask_name mask_align.mrc ccmask_name none \
            "${EULER[@]}" \
            calc_exp 0 calc_ctf 0 cos_weight 0 score_weight 1 \
            symmetry C1 score_thresh 0 subset 100 avg_mode full \
            ignore_halfsets 0 temperature 0 rot_mode linear fthresh 800
    done
    stage run_mraseed sg_run params/mraseed_param.star
    # Seed refs written at iteration=$ITER (avg_* mode does not increment iteration)

    # 7c) Multireference alignment+classification (5 iterations) per k
    # Note: ali_multiref at startidx=$ITER reads seed refs at $ITER (same as seed avg output).
    # If you see "reference not found" errors, check whether the seed avg wrote refs at
    # $ITER or $((ITER+1)) and adjust startidx accordingly.
    for k in "${KS[@]}"; do
        stage "parse_mra_k$k" $STOPGAPHOME/bin/stopgap_parser.sh subtomo \
            param_name params/mra_k${k}.star \
            rootdir "$ROOTS" "${DIRNONE[@]}" "${FILTNONE[@]}" \
            subtomo_mode ali_multiref startidx $ITER iterations 5 binning 1 \
            motl_name allmotl_mra_k$k wedgelist_name wedgelist.star \
            ref_name ref_mra_k$k subtomo_name subtomo \
            mask_name mask_align.mrc ccmask_name mask_cc.mrc \
            "${EULER[@]}" "${MRA_INPLANE[@]}"

        stage "run_mra_k$k" sg_run params/mra_k${k}.star
    done

    # 7d) Cross-method comparison: ARI/NMI + co-occurrence PNGs
    stage compare mlbatch \
        "compare_methods('$ROOT','lists/allmotl_pca_k%d_*.star','lists/allmotl_mra_k%d_*.star',[${KS[*]}]);"
    assert_exists "$ROOT/meta/pca_vs_mra_agreement.csv"

fi

echo ""
echo "=== run_pipeline.slurm finished cleanly ==="
echo "    PNGs and metrics : $ROOT/meta/"
echo "    Class averages   : $ROOT/ref/"
echo "    Motls            : $ROOT/lists/"
