# RELION  
- **Prerequisites:** Install build tools and libraries:  
  ```bash
  sudo yum install -y cmake git gcc gcc-c++ openmpi-devel fftw-devel libtiff-devel libpng-devel ghostscript libXft-devel libX11-devel
  ```  
  These include the C/C++ compiler, MPI, FFTW, TIFF/PNG support, X11 libraries and Ghostscript【5†L135-L139】. Ensure the NVIDIA driver and CUDA toolkit (11.x or newer) are installed on RHEL for GPU support (RELION auto-detects CUDA【2†L76-L83】).  
- **Build RELION from source:**  
  ```bash
  git clone --branch 5.0 https://github.com/3dem/relion.git
  cd relion
  mkdir build && cd build
  cmake .. -DCMAKE_BUILD_TYPE=Release -DENABLE_OPTIMIZE_MACHINE=ON  # Add -DCUDA_TOOLKIT_ROOT_DIR=/usr/local/cuda if needed
  make -j8
  sudo make install
  ```  
  By default, RELION builds with CUDA for NVIDIA GPUs if CUDA is detected【2†L76-L83】. Adjust `-DCUDA_TOOLKIT_ROOT_DIR` if CMake can’t find CUDA.  
- **Verify installation:** Run `relion --version` or `relion` to see the help. If missing libraries show up, install them (e.g. any “not found” in `ldd relion`).  
- **Troubleshooting:** Ensure all dependencies (especially FFTW and MPI) were installed. If GPU jobs fail, check that the CUDA driver version matches the toolkit.

# EMAN2  
- **Prerequisites:** Ensure OpenGL development libraries are installed for GUI (e.g. `mesa-libGL-devel`, `mesa-libGLU-devel`). On RHEL:  
  ```bash
  sudo yum install -y mesa-libGL-devel mesa-libGLU-devel libX11-devel libXft-devel libICE-devel libSM-devel zlib-devel
  ```  
  Also install Git, CMake and compilers. EMAN2 relies on Python 3 (via conda) and JAX/TensorFlow for GPU processing【20†L207-L215】.  
- **Set up conda environment:** We recommend [Miniforge](https://github.com/conda-forge/miniforge) or a conda-forge Python 3.12 install. Then create an EMAN2 environment:  
  ```bash
  conda create -n eman2 eman-dev --only-deps -c conda-forge -c cryoem  # installs EMAN2 dependencies
  conda activate eman2
  ```  
  For GPU acceleration, install JAX with CUDA (e.g. CUDA 12) via pip:  
  ```bash
  pip install "jax[cuda12]" optax
  ```  
  This ensures EMAN2’s deep-learning tools use NVIDIA GPUs【20†L207-L215】.  
- **Build EMAN2:**  
  ```bash
  git clone https://github.com/cryoem/eman2.git ~/src/eman2
  mkdir ~/build/eman2 && cd ~/build/eman2
  cmake ~/src/eman2 -DENABLE_OPTIMIZE_MACHINE=ON
  make -j8
  sudo make install
  ```  
  (Add `-DCMAKE_INSTALL_PREFIX=/usr/local` if needed.)  
- **Verify:** After installation, run `e2version.py`. If it prints version info (with Python and Linux versions), the install succeeded【20†L295-L304】. If GUI tools (like `e2display.py`) fail, ensure OpenGL drivers are correct (install Mesa headers).  
- **Troubleshooting:** If CMake cannot find dependencies, try setting `CONDA_PREFIX` or clean cache and re-run CMake. If OpenGL errors occur, install/upgrade Nvidia drivers and Mesa (e.g. `sudo yum install mesa-libGLU-devel`).

# emClarity  
- **Prerequisites:** emClarity is provided as a MATLAB-compiled binary (no build needed) but requires the MATLAB Runtime (MCR). Use **R2021a** MCR (v9.10) for emClarity v1.6.1【37†L48-L56】.  
- **Install MATLAB Runtime:** Download and run the Linux MCR installer:  
  ```bash
  wget https://ssd.mathworks.com/supportfiles/downloads/R2021a/Release/8/deployment_files/installer/complete/glnxa64/MATLAB_Runtime_R2021a_Update_8_glnxa64.zip
  unzip MATLAB_Runtime_R2021a_Update_8_glnxa64.zip -d mcr_installer
  cd mcr_installer
  sudo ./install -agreeToLicense yes
  ```  
- **Set environment:** After install, set `LD_LIBRARY_PATH` to include the MCR directories (as detailed by MathWorks). For example:  
  ```bash
  export MCR_ROOT=/usr/local/MATLAB/MATLAB_Runtime/v910
  export LD_LIBRARY_PATH=$MCR_ROOT/runtime/glnxa64:$MCR_ROOT/bin/glnxa64:$MCR_ROOT/sys/os/glnxa64:$MCR_ROOT/extern/bin/glnxa64:$LD_LIBRARY_PATH
  ```  
- **Download emClarity:** Obtain the latest release (e.g. v1.6.1) from the [emClarity Wiki](https://github.com/StochasticAnalytics/emClarity/wiki) or release page. For example:  
  ```bash
  wget https://github.com/StochasticAnalytics/emClarity/releases/download/v1.6.1/emClarity_1.6.1.0_v21a.zip
  unzip emClarity_1.6.1.0_v21a.zip -d ~/emclarity
  ```  
- **Configure emClarity:** Edit the emClarity launch script (e.g. `emclarity_1.6.1.0_v21a`) to set the MCR path. In it, set:  
  ```bash
  MCR_BASH=$MCR_ROOT/runtime/glnxa64:$MCR_ROOT/bin/glnxa64:$MCR_ROOT/sys/os/glnxa64:$MCR_ROOT/extern/bin/glnxa64
  export emClarity_ROOT=~/emclarity/emClarity_1.6.1.0
  export LD_LIBRARY_PATH=${emClarity_ROOT}/lib:${MCR_BASH}:${LD_LIBRARY_PATH}
  ```  
  Also add an alias, e.g. in `~/.bashrc`:  
  ```bash
  alias emClarity="~/emclarity/emClarity_1.6.1.0/bin/emClarity_1_6_1_0_v21a"
  ```  
  (Adjust paths as needed.)【37†L99-L107】  
- **Verify:** Run `emClarity check`. It should report the installation status. A full test can be done by `cd tomodrgn/testing; python ./quicktest.py` as suggested in documentation【56†L317-L322】 (though that’s for TomoDRGN; for emClarity use the built-in `emClarity check`).  
- **Troubleshooting:** If “undefined library path” errors occur, recheck `I3ROOT`/`MCR_BASH` settings. The MCR installer adds to `/usr/local/MATLAB`; ensure `LD_LIBRARY_PATH` covers those. If emClarity fails to find CUDA, ensure `nvcc` or `cuda` is in the PATH as the documentation notes【37†L42-L45】.

# STOPGAP  
- **Prerequisites:** STOPGAP is MATLAB-based. No compilation is required, but you need MATLAB (or the MATLAB Runtime matching the version used) installed. It runs on CPU; a GPU is not needed. You may also need [IMOD](https://bio3d.colorado.edu/imod/) and [CTFFIND4](https://grigoriefflab.umassmed.edu/ctf-installation) in your PATH for tomogram processing.  
- **Install:** Clone or download STOPGAP:  
  ```bash
  cd /opt
  sudo git clone https://github.com/wan-lab-vanderbilt/STOPGAP.git
  ```  
- **Configuration:** Add STOPGAP to MATLAB path. For example, in MATLAB run:  
  ```matlab
  addpath(genpath('/opt/STOPGAP'));
  savepath;
  ```  
  Or, to use the compiled version (if available), install the MATLAB Runtime matching STOPGAP’s build. Set an environment variable, e.g.:  
  ```bash
  export STOPGAP_ROOT=/opt/STOPGAP
  alias stopgap='$STOPGAP_ROOT/STOPGAP.sh'  # if a wrapper script exists
  ```  
- **Verify:** In MATLAB, type `stopgap` (or `help STOPGAP`). It should display STOPGAP help. For the standalone version, ensure scripts run without MATLAB (using provided `STOPGAP.sh`).  
- **Troubleshooting:** If functions fail, ensure all required toolboxes (Signal Processing, Image Processing) are licensed in MATLAB. If using the Runtime, confirm `LD_LIBRARY_PATH` includes the MCR libraries.

# Dynamo  
- **Prerequisites:** Dynamo is distributed as a MATLAB package with a free MCR. Download the appropriate Linux tarball from [Dynamo Downloads](https://www.dynamo-em.org). Ensure you have a supported NVIDIA driver and CUDA (≥7.5) for GPU use【52†L75-L83】.  
- **Install Dynamo:**  
  ```bash
  cd /opt
  sudo tar -xjf /path/to/dynamo2.0.X.tar.bz2 -C .
  ```  
  This creates `/opt/dynamo-2.0.X`. Replace with the actual version. No compilation is needed【51†L44-L52】.  
- **Activate Dynamo:**  
  - *Within MATLAB:* Start MATLAB and run: `run /opt/dynamo-2.0.X/dynamo_activate.m`. Then you can use Dynamo commands (e.g. `dynamo;`).  
  - *Standalone:* In a shell, run:  
    ```bash
    source /opt/dynamo-2.0.X/dynamo_activate_linux_shipped_MCR.sh
    dynamo
    ```  
    The first invocation will initialize the MCR, which may take a minute【51†L77-L87】. Subsequent starts are faster.  
- **GPU Tools:** To enable GPUs, recompile Dynamo’s GPU code:  
  ```bash
  cd /opt/dynamo-2.0.X/cuda
  which nvcc        # verify CUDA is in PATH
  source config.sh  # sets CUDA_ROOT in Makefile
  make clean
  make all
  ```  
  Ensure `CUDA_ROOT` in the Makefile matches your CUDA install【52†L47-L56】【52†L57-L66】. Also export the CUDA libs:  
  ```bash
  export LD_LIBRARY_PATH=/usr/local/cuda/lib64:$LD_LIBRARY_PATH
  ```  
  (Adjust `/usr/local/cuda` to your CUDA path.)【52†L97-L106】  
- **Verify:** In MATLAB or shell, run `dynamo` to see the Dynamo prompt or GUI. In MATLAB you should see the Dynamo menu【51†L62-L70】. For GPUs, run `nvidia-smi` to list devices and ensure Dynamo sees them.  
- **Troubleshooting:** If “CUDA version mismatch” errors appear, re-run `config.sh`. If Dynamo won’t start, try `source /opt/dynamo-2.0.X/dynamo_activate_linux.sh` to use a system MCR and ensure `$LD_LIBRARY_PATH` includes the MCR path【51†L95-L104】.

# Warp (WarpTools)  
- **Prerequisites:** Warp is distributed via conda. Ensure you have a recent NVIDIA driver and CUDA (≥11.8) on your RHEL machine. Install [Mambaforge](https://github.com/conda-forge/miniforge) or Anaconda for Python/conda.  
- **Create conda env & install WarpTools:**  
  ```bash
  conda create -n warp python=3.10   # or use base for anaconda
  conda activate warp
  conda install -c warpem -c nvidia/label/cuda-11.8.0 -c pytorch -c conda-forge warp=2.0.0
  ```  
  This installs `warp` (WarpTools) and dependencies, using the `warpem` channel and CUDA 11.8 build【54†L104-L110】.  
- **Verify:** Run `warp --help` or `conda list warp`【54†L118-L122】. The output should list Warp v2.0.0.  
- **Troubleshooting:** If `warp` command is missing, ensure the conda env is active. For GPU issues, confirm the CUDA driver matches the toolkit (11.8) used.

# TomoDRGN  
- **Prerequisites:** Requires Python 3.7+, PyTorch with GPU support, and CUDA ≥11.0. Install a CUDA toolkit (11.0+) on RHEL.  
- **Set up environment:**  
  ```bash
  conda create --name tomodrgn python=3.9
  conda activate tomodrgn
  # Install PyTorch with CUDA (>=11.0):
  conda install pytorch-gpu cudatoolkit=11.3 -c pytorch
  # Other dependencies:
  conda install pandas seaborn scikit-learn -c conda-forge
  conda install umap-learn notebook -c conda-forge
  pip install "ipyvolume>=0.6.0" "pythreejs>=2.4.2"
  ```  
  (Versions follow the [TomoDRGN documentation](【56†L302-L310】).)  
- **Install TomoDRGN:** Clone and install via pip:  
  ```bash
  git clone https://github.com/bpowell122/tomodrgn.git
  cd tomodrgn
  pip install .
  ```  
  (The repository and installation might redirect; use the official source.)  
- **Verify:** Run the provided tests:  
  ```bash
  cd tomodrgn/testing
  python ./quicktest.py   # short sanity check
  python ./unittest.py    # full test suite (~30 min)
  ```  
  These will confirm network training and inference work【56†L317-L322】. Also try a help command like `tomodrgn train_nn --help`.  
- **Troubleshooting:** If PyTorch cannot find the GPU, check `nvidia-smi` and CUDA paths. Ensure `LD_LIBRARY_PATH` includes the CUDA libraries if needed. If import errors occur, reinstall missing Python packages.

# MiLoPYP  
- **Prerequisites:** Tested on CentOS/RHEL 8 with Python 3.8, PyTorch 1.11.0 and CUDA 10.2【61†L56-L64】. Ensure CUDA 10.2 is installed on RHEL (e.g. via NVIDIA’s CUDA repo).  
- **Set up conda env:**  
  ```bash
  conda create --name MiLoPYP python=3.8
  conda activate MiLoPYP
  ```  
- **Clone & install MiLoPYP:** (the code is named `cet_pick` in GitHub)  
  ```bash
  git clone https://github.com/nextpyp/cet_pick.git
  pip install -r cet_pick/requirements.txt
  pip install torch==1.11.0+cu102 torchvision==0.12.0+cu102 torchaudio==0.11.0 --extra-index-url https://download.pytorch.org/whl/cu102
  pip install -e cet_pick
  ```  
  The first pip line installs dependencies; the second installs PyTorch wheels for CUDA 10.2【61†L79-L87】. The last installs the MiLoPYP package.  
- **Verify:** Run example scripts or the quick tutorials as described in the docs. For example, try a dummy run of `python cet_pick/test.py` (if available) or ensure `import cet_pick` works in Python.  
- **Troubleshooting:** If CUDA errors appear, double-check the PyTorch CUDA version (`nvcc --version`). For any missing Python packages, re-run `pip install` for the required module.

# Protomo (ElectronTomography)  
- **Prerequisites:** Install dependencies listed in the Protomo manual【64†L141-L149】【64†L163-L171】:  
  ```bash
  sudo yum install -y libtiff-devel fftw-devel lapack-devel blas-devel \
                      gtk2-devel gtkglext-devel plotutils ghostscript gv
  sudo yum install -y gcc-gfortran   # for Fortran LAPACK/BLAS if needed
  ```  
  These cover TIFF, FFTW2, MINPACK/LAPACK, GTK+, GtkGLExt, GNU plotutils and a PostScript viewer (Ghostscript or gv).  
- **Download & extract Protomo:**  
  Download `protomo-3.1.0.tar.bz2` from [electrontomography.org](https://electrontomography.org) (or [GitHub](https://github.com/protomo/protomo) if available). Then:  
  ```bash
  cd /usr/local
  sudo tar -xjf /path/to/protomo-3.1.0.tar.bz2 -C /usr/local
  ```  
  This creates `/usr/local/protomo-3.1.0`【63†L189-L197】.  
- **Configure Protomo:** Edit `setup.sh` in `/usr/local/protomo-3.1.0`: set  
  ```bash
  I3ROOT=/usr/local/protomo-3.1.0
  I3DEPLIB=<path_to_system_libs>    # e.g. /usr/lib64 for FFTW, etc.
  ```  
  (Typically point `I3DEPLIB` to where FFTW, LAPACK, etc., are installed; you may symlink system libs into `I3DEPLIB` to match names【63†L197-L205】.) Source the script:  
  ```bash
  source /usr/local/protomo-3.1.0/setup.sh
  ```  
  or add it to your `~/.bashrc`. Ensure `PATH` and `LD_LIBRARY_PATH` include the Protomo `bin` and lib directories as needed【63†L205-L214】.  
- **Verify:** Run `protomohow?` or a Protomo command (e.g. `ptomo` if that’s provided) to see if it starts. Alternatively, try `ldd` on a Protomo binary to confirm no “not found” libraries.  
- **Troubleshooting:** If errors mention missing libraries, install those packages or fix `I3DEPLIB`. The manual notes “undefined or invalid library path” means `I3ROOT` is wrong【63†L219-L227】. Also ensure GTK and OpenGL are installed for any GUI components.

**Sources:** Official docs and guides for each package【5†L135-L139】【20†L190-L197】【37†L50-L58】【51†L44-L52】【52†L57-L66】【54†L104-L110】【56†L302-L310】【61†L61-L69】【63†L189-L197】.