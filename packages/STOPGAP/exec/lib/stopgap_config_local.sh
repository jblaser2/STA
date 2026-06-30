## stopgap_config_local.sh
# Sources MATLAB r2023b runtime directories for local (non-SLURM) runs.
# BYU RC cluster: /apps/matlab/r2023b is the full MATLAB install.
#
# WW 06-2019 | updated for r2023b 2025

matlabRoot="/home/jblaser2/Applications/matlab/"
export LD_LIBRARY_PATH="$matlabRoot/runtime/glnxa64/${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
export LD_LIBRARY_PATH=${LD_LIBRARY_PATH}":$matlabRoot/bin/glnxa64/"
export LD_LIBRARY_PATH=${LD_LIBRARY_PATH}":$matlabRoot/sys/os/glnxa64/"
export LD_LIBRARY_PATH=${LD_LIBRARY_PATH}":$matlabRoot/sys/opengl/lib/glnxa64/"
echo "MATLAB r2023b libraries sourced..."
