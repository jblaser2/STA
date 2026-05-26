#!/usr/bin/env bash
## compileStopgap.sh
# Compiles STOPGAP against MATLAB r2023b MCR on an HPC cluster.
# Submit as a SLURM job (single node, single core, ~1 hour wall time).
# After completion, update exec/lib/stopgap_config_slurm.sh with the
# MCR path printed by this script.
#
# Usage:
#   Edit STOPGAP_SRC and MATLAB_ROOT below, then:
#   sbatch compileStopgap.sh

#SBATCH --job-name=compile_stopgap
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4          # MCC can parallelise internally
#SBATCH --mem=8G
#SBATCH --time=00:30:00
#SBATCH --output=compile_stopgap_%j.log
#SBATCH --error=compile_stopgap_%j.err

set -e
set -o nounset

# ---- USER CONFIGURATION ----------------------------------------------------
STOPGAP_SRC='/home/ejl62/summerResearch/STOPGAP'    # root of the STOPGAP checkout
# ---------------------------------------------------------------------------

# Load MATLAB r2023b
module load matlab/r2023b

# Resolve MATLAB root from the loaded module
MATLAB_ROOT=$(matlab -e 2>&1 | grep '^MATLAB =' | awk '{print $3}')
if [ -z "${MATLAB_ROOT}" ]; then
    # Fallback: derive from the matlab binary path
    MATLAB_ROOT=$(dirname $(dirname $(which matlab)))
fi
echo "Using MATLAB root: ${MATLAB_ROOT}"

# Compilation output goes directly into exec/lib/ so the shell wrappers
# in exec/bin/ can find the binaries without any extra copying.
COMPILE_TARGET="${STOPGAP_SRC}/exec/lib/"
mkdir -p "${COMPILE_TARGET}"

echo "Compiling STOPGAP into: ${COMPILE_TARGET}"

# Write MATLAB commands to a temp file to avoid multiline -r quoting issues
# on some cluster MATLAB wrappers. compile_toolbox.m is intentionally bypassed
# because it hardcodes the developer's /dors/wan_lab/ paths and MATLAB 2020b.
# We replicate its mcc call with the correct local paths instead.
COMPILE_SCRIPT=$(mktemp /tmp/sg_compile_XXXXXX.m)
cat > "${COMPILE_SCRIPT}" << MATLAB_EOF
addpath(genpath('${STOPGAP_SRC}/src'));
addpath(genpath('${STOPGAP_SRC}/sg_toolbox'));
target_dir = '${COMPILE_TARGET}';
disp('Starting compilation...');
tic;

% --- parser, stopgap, watcher (no hardcoded paths in these) ---
cd('${STOPGAP_SRC}/src/stopgap');
disp('  compile_parser...');  compile_parser(target_dir);
disp('  compile_stopgap...'); compile_stopgap(target_dir);
disp('  compile_watcher...'); compile_watcher(target_dir);

% --- toolbox (bypasses compile_toolbox.m which has hardcoded developer paths) ---
disp('  compile_toolbox...');
cd('${STOPGAP_SRC}/sg_toolbox/standalone');
t = target_dir;
if t(end) ~= '/', t = [t '/']; end
mcc('-R', '-nosplash', '-d', t, '-mv', 'sg_toolbox.m', ...
    '-a', '${STOPGAP_SRC}/sg_toolbox/', ...
    '-a', '${MATLAB_ROOT}/toolbox/matlab/graph2d/');
system(['chmod +x ' t 'sg_toolbox']);

fprintf('Compilation finished in %.1f minutes.\n', toc/60);
MATLAB_EOF

matlab -nodisplay -nosplash -r "run('${COMPILE_SCRIPT}'); exit;"
rm -f "${COMPILE_SCRIPT}"

echo ""
echo "=== Compilation complete. Verifying outputs ==="
for binary in stopgap stopgap_watcher stopgap_parser sg_toolbox; do
    if [ -f "${COMPILE_TARGET}/${binary}" ]; then
        echo "  OK: ${binary}  ($(du -sh ${COMPILE_TARGET}/${binary} | cut -f1))"
    else
        echo "  MISSING: ${binary} — check compile log for errors"
    fi
done

echo ""
echo "=== Next step: update exec/lib/stopgap_config_slurm.sh ==="
echo "Replace the matlabRoot line with:"
echo "  matlabRoot=\"${MATLAB_ROOT}/\""
echo ""
echo "The four LD_LIBRARY_PATH lines should become:"
echo "  export LD_LIBRARY_PATH=\${LD_LIBRARY_PATH}\":${MATLAB_ROOT}/runtime/glnxa64/\""
echo "  export LD_LIBRARY_PATH=\${LD_LIBRARY_PATH}\":${MATLAB_ROOT}/bin/glnxa64/\""
echo "  export LD_LIBRARY_PATH=\${LD_LIBRARY_PATH}\":${MATLAB_ROOT}/sys/os/glnxa64/\""
echo "  export LD_LIBRARY_PATH=\${LD_LIBRARY_PATH}\":${MATLAB_ROOT}/sys/opengl/lib/glnxa64/\""
echo ""
echo "Remove the glibc-2.17_shim.so LD_PRELOAD line — it was 2020b-specific."
