#!/bin/bash
#SBATCH --job-name=pili_resume
#SBATCH --nodes=1
#SBATCH --ntasks=64
#SBATCH --cpus-per-task=1
#SBATCH --mem-per-cpu=4G
#SBATCH --time=2:00:00
#SBATCH -o pili_resume_%j.log
#SBATCH -e pili_resume_%j.err
set -Eeuo pipefail

# Resume the PCA branch of run_pipeline.slurm from the kmeans stage, reusing the
# existing PCA outputs (eigenval CSVs, rvol/rwei volumes) from job 12090301.
# Runs: kmeans -> class averages (run_avg_pca) -> visualization (viz_pca).
# Does NOT recompute alignment or PCA. MRA is intentionally left out (separate,
# long compute that does not depend on the PCA results).

############################ USER CONFIG ############################
SG=/home/ejl62/summerResearch/STA/STOPGAP
export STOPGAPHOME=$SG/exec
ROOT=/home/ejl62/Pili_class
KS=(2 3 4)
ITER=3                                  # DO_ALIGN produced allmotl_3
PX=AUTO
NC=$SLURM_NTASKS
####################################################################

module load matlab/r2023b
MLP="addpath(genpath('$SG/src'));addpath(genpath('$SG/sg_toolbox'));addpath('$SG/scripts');"

mkdir -p "$ROOT" "$ROOT/logs"
cd "$ROOT"
ROOTS="${ROOT%/}/"

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
mlbatch() { matlab -nodisplay -nosplash -batch "$MLP $1"; }
sg_run() { srun --ntasks=$NC --cpus-per-task=1 \
    $STOPGAPHOME/bin/stopgap_mpi_slurm.sh "$ROOT" "$1" $NC 0 slurm; }

DIRNONE=(tempdir none commdir none rawdir none refdir none maskdir none \
         listdir none fscdir none subtomodir none metadir none)
FILTNONE=(ali_reffilter_name none ali_particlefilter_name none \
          avg_reffilter_name none avg_particlefilter_name none \
          reffiltertype none particlefiltertype none \
          specdir none ps_name none amp_name none specmask_name none)
EULER=(euler_axes zxy euler_1_incr 1 euler_1_iter 1 \
       euler_2_incr 1 euler_2_iter 3 euler_3_incr 1 euler_3_iter 1)

# Sanity: required PCA outputs must already exist
assert_exists "$ROOT/pca/eigenval_1.csv"
assert_exists "$ROOT/lists/allmotl_${ITER}.star"

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
# Parser APPENDS rows; clear any stale avg param + comm coordination first.
rm -f "$ROOT"/params/avg_pca_param.star 2>/dev/null || true
rm -f "$ROOT"/comm/* 2>/dev/null || true

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

echo ""
echo "=== resume_pca.slurm finished cleanly ==="
echo "    Visualizations : $ROOT/meta/"
echo "    Class averages : $ROOT/ref/"
echo "    Motls          : $ROOT/lists/"
