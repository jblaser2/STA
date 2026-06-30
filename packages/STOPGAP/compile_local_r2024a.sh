#!/bin/bash
# compile_local_r2024a.sh — compile STOPGAP binaries using MATLAB R2024a on Josh's node.
#
# Adapted from recompile_stopgap.slurm (Eben's R2023b cluster version).
# Differences:
#   - No SLURM; runs directly
#   - Uses ~/Applications/matlab (R2024a) instead of /apps/matlab/r2023b
#   - Binaries land in exec/lib_r2024a/ then are installed to exec/lib/
#
# Usage: bash packages/STOPGAP/compile_local_r2024a.sh
# Runtime: ~30–60 min (mcc compiles each binary serially)

set -Eeuo pipefail
trap 'echo "ACHTUNG!!! compile failed at line $LINENO: $BASH_COMMAND" >&2; exit 1' ERR

SG=/home/jblaser2/Research/STA/packages/STOPGAP
MATLAB=/home/jblaser2/Applications/matlab
OUT=$SG/exec/lib_r2024a

export PATH="$MATLAB/bin:$PATH"

command -v mcc >/dev/null || { echo "ACHTUNG!!! mcc not found in $MATLAB/bin"; exit 1; }
echo "mcc: $(which mcc)"
echo "MATLAB root: $MATLAB"

# Patch compile_toolbox.m paths to this machine
sed -i "s|^sg_toolbox_dir = .*|sg_toolbox_dir = '$SG/sg_toolbox/';|" \
    "$SG/src/stopgap/compile_toolbox.m"
sed -i "s|^matlab_root = .*|matlab_root = '$MATLAB/';|" \
    "$SG/src/stopgap/compile_toolbox.m"

# Update MCR path in all three config variants to point at R2024a
for cfg in stopgap_config_slurm.sh stopgap_config_local.sh stopgap_config.sh; do
    f="$SG/exec/lib/$cfg"
    [ -f "$f" ] || cp "$SG/exec/lib/stopgap_config_slurm.sh" "$f"
    sed -i "s|^matlabRoot=.*|matlabRoot=\"$MATLAB/\"|" "$f"
done

mkdir -p "$OUT"
cd "$SG"

# Write compile commands to a .m file — MATLAB -batch doesn't handle multi-line shell strings
COMPILE_M="/tmp/sg_compile_${$}.m"
cat > "$COMPILE_M" << MEOF
addpath(genpath('$SG/src'));
addpath(genpath('$SG/sg_toolbox'));
compile_parser('$OUT');
compile_stopgap('$OUT');
compile_watcher('$OUT');
compile_toolbox('$OUT');
MEOF

echo ""
echo "=== Compiling STOPGAP binaries for MATLAB R2024a ==="
echo "    Output: $OUT"
echo "    Started: $(date)"
echo ""

"$MATLAB/bin/matlab" -nodisplay -nosplash -batch "run('$COMPILE_M')"
rm -f "$COMPILE_M"

echo ""
echo "=== Verifying binaries ==="
for b in stopgap stopgap_parser stopgap_watcher sg_toolbox; do
    if [ -x "$OUT/$b" ]; then
        echo "  OK: $b"
    else
        echo "ACHTUNG!!! missing or non-executable binary: $OUT/$b"
        exit 1
    fi
done

# Backup existing binaries, then install new ones
mkdir -p "$SG/exec/lib_prev"
for b in stopgap stopgap_parser stopgap_watcher sg_toolbox; do
    [ -f "$SG/exec/lib/$b" ] && cp -f "$SG/exec/lib/$b" "$SG/exec/lib_prev/" 2>/dev/null || true
done
cp "$OUT"/{stopgap,stopgap_parser,stopgap_watcher,sg_toolbox} "$SG/exec/lib/"
chmod +x "$SG"/exec/lib/{stopgap,stopgap_parser,stopgap_watcher,sg_toolbox}

# Smoke test: parser should produce a .star param file
export STOPGAPHOME=$SG/exec
TMPD=$(mktemp -d)
mkdir -p "$TMPD/params"
echo ""
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
    echo "COMPILE OK — parser produced pca_param.star"
else
    echo "ACHTUNG!!! smoke test failed: no pca_param.star produced"
    exit 1
fi
rm -rf "$TMPD"

echo ""
echo "=== compile_local_r2024a.sh finished cleanly ==="
echo "    Finished: $(date)"
echo "    Binaries: $SG/exec/lib/{stopgap,stopgap_parser,stopgap_watcher,sg_toolbox}"
