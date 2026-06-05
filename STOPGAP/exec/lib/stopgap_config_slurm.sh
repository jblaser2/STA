## stopgap_config_slurm.sh
# Sources MATLAB r2023b runtime directories required to run STOPGAP on SLURM.
# BYU RC cluster: /apps/matlab/r2023b is the full MATLAB install; no separate
# MCR module for r2023b, so we use the runtime libs from the full install.
#
# WW 06-2019 | updated for r2023b 2025

matlabRoot="/apps/matlab/r2023b/"
export LD_LIBRARY_PATH="$matlabRoot/runtime/glnxa64/${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
export LD_LIBRARY_PATH=${LD_LIBRARY_PATH}":$matlabRoot/bin/glnxa64/"
export LD_LIBRARY_PATH=${LD_LIBRARY_PATH}":$matlabRoot/sys/os/glnxa64/"
export LD_LIBRARY_PATH=${LD_LIBRARY_PATH}":$matlabRoot/sys/opengl/lib/glnxa64/"
echo "MATLAB r2023b libraries sourced..."
