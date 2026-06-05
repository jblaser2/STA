#!/bin/bash
#SBATCH --job-name=sg_compile
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=16G
#SBATCH --time=01:00:00
#SBATCH -o sg_compile_%j.log
#SBATCH -e sg_compile_%j.err
set -Eeuo pipefail
trap 'echo "ACHTUNG!!! compile failed at line $LINENO: $BASH_COMMAND" >&2; exit 1' ERR

SG=/home/ejl62/summerResearch/STA/STOPGAP
OUT=$SG/exec/lib_r2023b

module load matlab/r2023b

# Pre-flight: mcc must be on PATH (ships inside the MATLAB install, not a separate module)
command -v mcc >/dev/null || { echo "ACHTUNG!!! mcc not on PATH after 'module load matlab/r2023b'"; exit 1; }
echo "mcc: $(which mcc)"

# source patches are already applied by direct edits; the sed below is idempotent
sed -i "s|^sg_toolbox_dir = .*|sg_toolbox_dir = '$SG/sg_toolbox/';|" \
    "$SG/src/stopgap/compile_toolbox.m"
sed -i "s|^matlab_root = .*|matlab_root = '/apps/matlab/r2023b/';|" \
    "$SG/src/stopgap/compile_toolbox.m"

# Ensure stopgap_config.sh exists (needed by stopgap_toolbox.sh)
for cfg in stopgap_config_slurm.sh stopgap_config_local.sh stopgap_config.sh; do
    if [ ! -f "$SG/exec/lib/$cfg" ]; then
        cp "$SG/exec/lib/stopgap_config_slurm.sh" "$SG/exec/lib/$cfg"
    fi
    # Ensure r2023b path in each config
    sed -i 's|^matlabRoot=.*|matlabRoot="/apps/matlab/r2023b/"|' "$SG/exec/lib/$cfg" || true
done

mkdir -p "$OUT"
cd "$SG"

echo "=== Compiling STOPGAP binaries for MATLAB r2023b ==="
matlab -nodisplay -nosplash -batch "\
  addpath(genpath('$SG/src')); addpath(genpath('$SG/sg_toolbox')); \
  compile_parser('$OUT'); \
  compile_stopgap('$OUT'); \
  compile_watcher('$OUT'); \
  compile_toolbox('$OUT');"

# Verify all four binaries were built
echo "=== Verifying binaries ==="
for b in stopgap stopgap_parser stopgap_watcher sg_toolbox; do
    if [ -x "$OUT/$b" ]; then
        echo "  OK: $b"
    else
        echo "ACHTUNG!!! missing or non-executable binary: $OUT/$b"
        exit 1
    fi
done

# Backup R2020b binaries if present, then install new ones
mkdir -p "$SG/exec/lib_r2020b"
for b in stopgap stopgap_parser stopgap_watcher sg_toolbox; do
    [ -f "$SG/exec/lib/$b" ] && cp -n "$SG/exec/lib/$b" "$SG/exec/lib_r2020b/" 2>/dev/null || true
done
cp "$OUT"/{stopgap,stopgap_parser,stopgap_watcher,sg_toolbox} "$SG/exec/lib/"
chmod +x "$SG"/exec/lib/{stopgap,stopgap_parser,stopgap_watcher,sg_toolbox}

# Smoke test: parser should write a param star file
export STOPGAPHOME=$SG/exec
TMPD=$(mktemp -d)
mkdir -p "$TMPD/params"
echo "=== Smoke test: pca parser ==="
(
  cd "$TMPD"
  bash $STOPGAPHOME/bin/stopgap_parser.sh pca \
    param_name params/pca_param.star \
    rootdir "$TMPD" tempdir none commdir none rawdir none refdir none \
    maskdir none listdir none subtomodir none rvoldir none pcadir none metadir none \
    pca_task rot_vol iteration 1 \
    motl_name allmotl wedgelist_name wedgelist.star binning 1 \
    ref_name ref mask_name mask.mrc subtomo_name subtomo \
    rvol_name rvol rwei_name rwei \
    filtlist_name filter_list.star data_type awpd \
    ccmat_name ccmatrix covar_name covar n_eigs 10 \
    eigenvol_name eigenvol eigenfac_name eigenfac eigenval_name eigenval \
    apply_laplacian 0 symmetry c1 fthresh 300
)
if [ -s "$TMPD/params/pca_param.star" ]; then
    echo "COMPILE OK: parser produced $TMPD/params/pca_param.star"
else
    echo "ACHTUNG!!! smoke test failed: no pca_param.star produced"
    exit 1
fi
rm -rf "$TMPD"

echo "=== recompile_stopgap.slurm finished cleanly ==="
echo "    Binaries in $SG/exec/lib/  (r2020b backup in exec/lib_r2020b/)"
