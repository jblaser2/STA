# STA Classification Benchmark — Package Installation Guide (RHEL 10)

**Project:** CryoET Subtomogram Classification Benchmarking  
**Target OS:** Red Hat Enterprise Linux 10 (x86_64)  
**Packages covered:** RELION 3.1–4.0, OPUS-TOMO, PEET, emClarity, I3/ProTomo, PyTom, DISCA, HEMNMA-3D, TomoFlow, MDTOMO, AC3D, TomoNet  
**Excluded (handled separately):** Dynamo, EMAN2, STOPGAP

---

## Preliminary: System-wide Prerequisites

Install these once before touching any individual package. All require `sudo` (or your sysadmin).

```bash
# Core build tools
sudo dnf groupinstall "Development Tools"
sudo dnf install -y cmake git wget curl \
    gcc gcc-c++ gcc-gfortran \
    openmpi openmpi-devel \
    fftw fftw-devel \
    libtiff libtiff-devel \
    libpng libpng-devel \
    libXft libXft-devel \
    libX11 libX11-devel \
    ghostscript \
    pbzip2 xz zstd \
    python3 python3-pip python3-devel

# Load OpenMPI into PATH (adjust module name if your cluster uses a different one)
module load mpi/openmpi-x86_64
# Or add to ~/.bashrc permanently:
# export PATH=/usr/lib64/openmpi/bin:$PATH
# export LD_LIBRARY_PATH=/usr/lib64/openmpi/lib:$LD_LIBRARY_PATH
```

**NVIDIA CUDA:** Most GPU-accelerated tools here require CUDA 11.x or 12.x. Install the appropriate CUDA toolkit from https://developer.nvidia.com/cuda-downloads and confirm with:
```bash
nvcc --version
nvidia-smi
```

**Conda (Miniconda/Miniforge):** Required by several packages. If not installed:
```bash
wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh
bash Miniconda3-latest-Linux-x86_64.sh -b -p $HOME/miniconda3
source $HOME/miniconda3/etc/profile.d/conda.sh
conda init bash
```

---

## 1. RELION 3.1 and 4.0

**What it is:** The workhorse package for maximum-likelihood 3D classification. For STA, both 3.1 (subtomogram mode) and 4.0 (tilt-series native mode) are used. You should install both in separate directories so both are accessible for the benchmark.

**Source:** https://github.com/3dem/relion  
**Docs:** https://relion.readthedocs.io/en/release-4.0/Installation.html

### System dependencies (add to what was installed above):
```bash
sudo dnf install -y ctffind  # or install from source; see below
```

### RELION 4.0 (recommended main install):

```bash
# Clone and checkout
git clone https://github.com/3dem/relion.git relion4
cd relion4
git checkout ver4.0
git pull

# Create build directory
mkdir build && cd build

# Configure — adjust CUDA_ARCH to match your GPU
# Ampere (A100, RTX 3090): 80
# Volta (V100): 70
# Turing (RTX 2080): 75
cmake -DCMAKE_INSTALL_PREFIX=/opt/relion4 \
      -DCUDA=ON \
      -DCudaTexture=ON \
      -DCUDA_ARCH=80 \
      -DMPI_INCLUDE_PATH=/usr/lib64/openmpi/include \
      -DMPI_C_COMPILER=mpicc \
      -DMPI_CXX_COMPILER=mpicxx \
      ..

make -j$(nproc)
make install
```

Add to `~/.bashrc`:
```bash
export PATH=/opt/relion4/bin:$PATH
```

### RELION 3.1 (legacy, for benchmarking the older subtomogram workflow):

```bash
git clone https://github.com/3dem/relion.git relion31
cd relion31
git checkout ver3.1

mkdir build && cd build
cmake -DCMAKE_INSTALL_PREFIX=/opt/relion31 \
      -DCUDA=ON \
      -DCudaTexture=ON \
      -DCUDA_ARCH=80 \
      ..
make -j$(nproc)
make install
```

### Python environment for RELION 4.0 class ranker (optional but useful):
```bash
conda create -n relion4py python=3.9
conda activate relion4py
pip install torch==1.10.0 numpy==1.20.0
```

### Quick sanity check:
```bash
/opt/relion4/bin/relion --version
/opt/relion31/bin/relion --version
```

> **RHEL 10 note:** RHEL 10 ships with a modern GCC (≥11) and glibc, so C++14 support is not an issue. The main pitfall is ensuring the CUDA toolkit version matches your driver. Run `nvidia-smi` to see the driver's maximum supported CUDA version and install a toolkit ≤ that version.

---

## 2. OPUS-TOMO (OPUS-ET)

**What it is:** Deep learning framework (VAE-based, similar to cryoDRGN) for simultaneous compositional and conformational heterogeneity analysis in cryo-ET. Works best with subtomograms preprocessed by WARP/M.

**Source:** https://github.com/alncat/opusTOMO  
**Preprint:** https://www.biorxiv.org/content/10.1101/2025.11.21.688990v1

> **Note:** The repository is actively updated. Run `git pull` before major use to stay current.

```bash
git clone https://github.com/alncat/opusTOMO.git
cd opusTOMO
```

### Conda environment (CUDA 11.3 + PyTorch 1.11):
```bash
conda env create --name opuset -f environment.yml
conda activate opuset
pip install -e .
```

If your system has CUDA 11.x (not 11.3 specifically):
```bash
# Try the cu11 variant instead:
conda env create --name opuset -f environmentcu11.yml
conda activate opuset
pip install -e .
```

If you have CUDA 11 and prefer PyTorch 1.11:
```bash
conda env create --name opuset -f environmentcu11torch11.yml
conda activate opuset
pip install -e .
```

### Verify installation:
```bash
conda activate opuset
dsd train_tomo -h
dsdsh analyze -h
```

### Data input note:
OPUS-TOMO reads RELION STAR files and subtomograms. It integrates tightly with the WARP pipeline for per-particle CTF export. For non-WARP inputs, use `dsdsh prepare` to convert STAR files to the required `.pkl` pose format:
```bash
# For RELION ≤3.0 STAR files:
dsdsh prepare /path/to/consensus_data.star <box_size> <angpix>

# For RELION ≥3.1 STAR files, add --relion31:
dsd parse_pose_star consensus_data.star -D <box_size> --Apix <angpix> --relion31 -o poses.pkl
```

---

## 3. PEET (Particle Estimation for Electron Tomography)

**What it is:** MATLAB-compiled subtomogram averaging + classification package from the Boulder Lab (Mastronarde/Heumann group). Includes PCA-based classification (described in Heumann et al. 2011). Ships with a bundled MATLAB Runtime — no MATLAB license needed.

**Source:** https://bio3d.colorado.edu/PEET  
**Requires:** IMOD (must be installed first)

### Step 1 — Install IMOD:
```bash
wget https://bio3d.colorado.edu/imod/AMD64-RHEL5/imod_4.11.25_RHEL7-64_CUDA10.0.sh
# Check the downloads page for the latest RHEL build:
# https://bio3d.colorado.edu/imod/download.html
chmod +x imod_*.sh
sudo ./imod_*.sh   # installs to /usr/local/IMOD by default
source /usr/local/IMOD/IMOD-linux.sh
```

> Check https://bio3d.colorado.edu/imod/download.html for the latest version. IMOD RHEL builds are labeled "RHEL7-64" but run fine on RHEL 8/9/10 due to backward-compatible glibc. If there is a RHEL 9 or 10 build available by the time you read this, prefer that.

### Step 2 — Download PEET:
PEET is downloaded separately from:  
https://bio3d.colorado.edu/PEET/

```bash
# Download the latest tarball from the PEET page, then:
tar xzf PEET_1-16-0_RHEL7-64.tar.gz -C /usr/local/
echo 'export PATH=/usr/local/PEET/bin:$PATH' >> ~/.bashrc
source ~/.bashrc
```

PEET includes its own Matlab Compiler Runtime (MCR) and does not require a Matlab license.

### Step 3 — Configure IMOD+PEET integration:
PEET integrates into IMOD's eTomo GUI. To access it:
```bash
etomo   # Select "Subvolume Averaging (PEET)" from the interface
```

### Verify:
```bash
peetMBFactor --help
avgPrm --help
```

---

## 4. emClarity

**What it is:** GPU-accelerated, fully integrated cryo-ET pipeline with iterative tilt-series refinement and multi-scale PCA classification. Compiled MATLAB binary (MCR 2019a or 2020b required). Notably, classification happens in 2D tilt-series space rather than on extracted 3D subtomograms, which is a key differentiator for your benchmark.

**Source:** https://github.com/emClarity/emClarity (binaries on Google Drive, linked from wiki)  
**Wiki:** https://github.com/bHimes/emClarity/wiki

> **⚠️ Important:** emClarity is no longer actively maintained (last stable release ~1.5.3.11). It runs but expect installation quirks. The MATLAB Runtime version must exactly match the binary.

### Step 1 — Download binary:
Visit https://github.com/bHimes/emClarity/wiki/Installation and download the binary bundle from the Google Drive link. As of the last stable release:
- Binary: `emClarity_1_5_3_11`
- Run script: `emClarity_1_5_3_11_v19a` (requires MCR 2019a) **or** `emClarity_1_5_3_11_v20b` (requires MCR 2020b)

```bash
mkdir /opt/emClarity
# Copy downloaded files there
```

### Step 2 — Install MATLAB Compiler Runtime (MCR 2020b recommended):
Download MCR R2020b Update 3 from MathWorks (free, no license needed):  
https://www.mathworks.com/products/compiler/matlab-runtime.html

```bash
mkdir $HOME/matlab_install && cd $HOME/matlab_install
# Unzip downloaded MCR installer
unzip MATLAB_Runtime_R2020b_Update_3_glnxa64.zip
mkdir -p /opt/matlab/R2020b
./install -mode silent -agreeToLicense yes -destinationFolder /opt/matlab/R2020b
```

Add to `~/.bashrc`:
```bash
MCR=/opt/matlab/R2020b
export LD_LIBRARY_PATH=$MCR/runtime/glnxa64:$MCR/bin/glnxa64:$MCR/sys/os/glnxa64:$LD_LIBRARY_PATH
export XAPPLRESDIR=$MCR/X11/app-defaults
```

### Step 3 — Set up emClarity dependencies (IMOD + CTFFIND):
emClarity requires IMOD (see PEET section above) and CTFFIND4:
```bash
# CTFFIND4 from https://grigoriefflab.umassmed.edu/ctffind4
wget https://grigoriefflab.umassmed.edu/sites/default/files/ctffind-4.1.14-linux64.tar.gz
tar xzf ctffind-4.1.14-linux64.tar.gz -C /opt/
echo 'export PATH=/opt/ctffind-4.1.14:$PATH' >> ~/.bashrc
```

### Step 4 — Configure and test:
```bash
cd /opt/emClarity
# Edit the run script to point to your MCR and IMOD:
# Find the line: MCR_ROOT= and set to /opt/matlab/R2020b
# Find: imodDir= and set to /usr/local/IMOD

bash emClarity_1_5_3_11_v20b   # Should print usage/help
```

> **Known RHEL 10 issue:** If you see `libGL error: MESA-LOADER: failed to open swrast`, install: `sudo dnf install mesa-libGL mesa-dri-drivers`. This is a display library issue that does not affect headless runs.

---

## 5. I3 / ProTomo

**What it is:** An older but still-cited STA package combining the I3 (image analysis) and ProTomo (tilt-series alignment) frameworks from the Forster group. Written in C; runs headlessly.

**Source:** http://www.electrontomography.org/  
**Status:** Legacy; not actively developed. Installation is more involved than modern packages.

### Download:
The I3 package is available from http://www.electrontomography.org/. Registration may be required. Download the Linux binary tarball.

```bash
mkdir /opt/i3
tar xzf i3_*.tar.gz -C /opt/i3
echo 'export PATH=/opt/i3/bin:$PATH' >> ~/.bashrc
echo 'export I3DIR=/opt/i3' >> ~/.bashrc
source ~/.bashrc
```

### Dependencies:
I3 is mostly self-contained but links against standard system libraries:
```bash
sudo dnf install -y libX11 libXt openmotif libgomp fftw
```

### ProTomo (tilt-series alignment component):
ProTomo is usually bundled with I3. If separate:
```bash
tar xzf protomo_*.tar.gz -C /opt/i3
```

### Verify:
```bash
i3align --help
i3av --help
```

> **Practical note for benchmarking:** I3/ProTomo is primarily a tilt-series alignment + STA pipeline. For your benchmarking project where you want to isolate the classification step, I3 is most relevant for users who ran their full pipeline within I3. The classification in I3 uses PCA + multivariate statistical analysis. This package may have the highest installation friction of any on this list. Consider whether the bandwidth is worth it for a 2-month project, or defer to a later phase.

---

## 6. PyTom

**What it is:** Python toolbox from the Förster lab (Utrecht University) covering reconstruction, template matching, alignment, and classification. All Python/conda managed. The STA classification functionality is in the main `PyTom` repo; the GPU-accelerated template matching has been split off to `pytom-match-pick`.

**Source:** https://github.com/SBC-Utrecht/PyTom  
**Docs/Wiki:** https://github.com/SBC-Utrecht/PyTom/wiki

```bash
git clone https://github.com/SBC-Utrecht/PyTom.git
cd PyTom
```

### Conda environment (handles all dependencies):
```bash
# The repo provides environment YAMLs for different CUDA versions
# Check environments/ for options; use the one matching your CUDA:
conda env create -f environments/pytom_full.yaml --name pytom_env
conda activate pytom_env

# Compile the backend (~5 minutes):
python setup.py install --prefix $CONDA_PREFIX
```

### Verify and launch GUI:
```bash
conda activate pytom_env
pytom --help
pytomGUI   # Opens the graphical interface (requires display)
```

### For headless/HPC use (classification without GUI):
PyTom classification scripts can be called directly:
```bash
pytom /path/to/PyTom/classification/classify.py --help
```

### Optional: pytom-match-pick (standalone GPU template matching):
```bash
conda create -n pytom_tm -c conda-forge python=3 cupy cuda-version=11.8
conda activate pytom_tm
git clone https://github.com/SBC-Utrecht/pytom-match-pick.git
cd pytom-match-pick
pip install '.[all]'
```

> **RHEL 10 note:** The `pytom_full.yaml` resolves most dependencies automatically. The most common issue is CUDA version mismatches in the cupy package. If conda hangs resolving, try `conda env create -f environments/pytom_full.yaml --name pytom_env --solver=libmamba` (requires `conda install conda-libmamba-solver`).

---

## 7. DISCA (Deep Iterative Subtomogram Clustering Approach)

**What it is:** Unsupervised deep learning clustering from the Xu Lab (CMU). Uses a CNN (YOPO) + EM framework to automatically determine the number of clusters without templates or labels. Published in PNAS 2023. Code is distributed as part of the `aitom` toolkit.

**Source:** https://github.com/xulabs/aitom

```bash
git clone https://github.com/xulabs/aitom.git
cd aitom
```

### Conda environment:
```bash
conda create -n aitom python=3.8
conda activate aitom
pip install -r requirements.txt
# Or install directly:
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
pip install numpy scipy scikit-learn mrcfile
pip install -e .
```

### Verify DISCA specifically:
```bash
python -c "import aitom.classification.deep.unsupervised.disca.disca as d; print('DISCA OK')"
```

### Running DISCA:
DISCA scripts live under `aitom/classification/deep/unsupervised/disca/`. The main entry point:
```bash
python aitom/classification/deep/unsupervised/disca/disca.py --help
```

Input is a set of pre-extracted subtomograms in MRC format or as a numpy array via a JSON config file. See the aitom wiki for example configs.

> **Note on scope:** DISCA is designed for large-scale *de novo* structural discovery (sorting mixed cellular content), rather than fine conformational classification of a single pre-aligned complex. It will likely underperform on your task of classifying assembly states of a single known complex. Include it as a baseline comparison, but this is an important caveat to document in your benchmark.

---

## 8. HEMNMA-3D, TomoFlow, and MDTOMO (ContinuousFlex / Scipion plugin)

**What they are:** All three methods are for **continuous conformational variability** analysis, not discrete classification. They are bundled as a single Scipion 3 plugin called `continuousflex`.

- **HEMNMA-3D:** Normal mode analysis-based conformational variability in subtomograms
- **TomoFlow:** Dense optical flow-based conformational analysis in subtomograms
- **MDTOMO:** Molecular dynamics-based atomic-resolution conformational landscape

**Source:** https://github.com/scipion-em/scipion-em-continuousflex  
**Requires:** Scipion 3 (workflow management framework)

### Step 1 — Install Scipion 3:
```bash
# Download the Scipion3 installer
wget https://scipion.i2pc.es/static/user_data/downloads/scipion3-installer.tar.gz
tar xzf scipion3-installer.tar.gz
cd scipion3-installer
./installer --help

# Install Scipion to a local directory (no sudo needed):
./installer -j $(nproc) scipion3

# Follow interactive prompts; when asked about conda, point to your existing Miniconda
```

Alternatively, install via conda:
```bash
conda create -n scipion3 python=3.8
conda activate scipion3
pip install scipion
scipion3 config  # Configure paths
```

Full install docs: https://scipion-em.github.io/docs/docs/scipion-modes/install-from-sources.html

### Step 2 — Install ContinuousFlex plugin:

From within Scipion, open the Plugin Manager (GUI) and install `scipion-em-continuousflex`, or from command line:
```bash
scipion3 installp -p scipion-em-continuousflex
```

Or install from PyPI directly into the Scipion environment:
```bash
conda activate scipion3
pip install scipion-em-continuousflex
```

### Step 3 — Verify each method:
```bash
# Run automated tests (each takes ~5–10 min with test data):
scipion3 tests continuousflex.tests.test_workflow_HEMNMA3D
scipion3 tests continuousflex.tests.test_workflow_TomoFlow
```

MDTOMO is also accessed via the continuousflex plugin in Scipion, under the `MDTOMO` protocol.

### Important prerequisites for MDTOMO:
MDTOMO requires an atomic model as input (PDB file) and the GENESIS MD simulation package:
```bash
# In the Scipion Plugin Manager, enable GENESIS under the continuousflex plugin
# Or install manually: https://github.com/genesis-release-r-ccs/genesis
```

> **Benchmark scope note:** HEMNMA-3D, TomoFlow, and MDTOMO all require an initial atomic model or reference EM map and are designed for *continuous* heterogeneity on a single known complex. They are not appropriate for the initial compositional sorting task (separating assembly states from junk particles). Use them in the "continuous heterogeneity" arm of your benchmark, and clearly document this distinction.

---

## 9. AC3D (Autofocused 3D Classification)

**What it is:** PCA + k-means clustering algorithm that automatically generates a focused mask based on the most structurally variable regions between class averages. Published in Structure 2014 (Chen et al.). No separate public repository — implemented within **PyTom**.

**Source:** Integrated into PyTom (see section 6 above).  
**Paper:** https://www.sciencedirect.com/science/article/pii/S0969212614002524

AC3D is accessed via PyTom's classification pipeline. Once PyTom is installed:
```bash
conda activate pytom_env
pytom /path/to/PyTom/classification/autofocused3DClassification.py --help
```

No separate installation is needed beyond PyTom. Confirm AC3D is available:
```bash
python -c "from pytom.classification.autofocused3DClassification import autoFocusClassify; print('AC3D OK')"
```

> **Note:** If the import path differs between PyTom versions, look for `ac3d` or `autofocus` in `pytom/classification/`. The algorithm is sometimes also referred to as "autofocused classification with PCA" in the PyTom docs.

---

## 10. TomoNet

**What it is:** Deep learning framework for cryo-ET processing including subtomogram classification using a 3D CNN. From Zeng et al. 2023 (PMC11140495).

**Source:** Search for the TomoNet GitHub — the repository may be under the author's lab page. The paper is: https://pmc.ncbi.nlm.nih.gov/articles/PMC11140495/

```bash
# Check the paper's data availability section for the current repo URL.
# As of writing, search: github.com tomonet cryo-ET classification
git clone https://github.com/<tomonet-repo>   # Replace with actual URL from paper
cd tomonet
```

### Conda environment:
```bash
conda create -n tomonet python=3.8
conda activate tomonet
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu118
pip install -r requirements.txt
```

> **⚠️ Important:** The TomoNet repository URL was not directly resolvable at time of writing. Check the supplementary materials or GitHub link in the PMC article at https://pmc.ncbi.nlm.nih.gov/articles/PMC11140495/ for the authoritative install instructions. If the repo is not public, contact the corresponding author directly — this is standard practice in the field and they will likely share it.

---

## Environment Summary Table

| Package | Conda env name | Python | CUDA needed | GPU needed | Scipion |
|---|---|---|---|---|---|
| RELION 4.0 | `relion4py` (optional, for ranker) | 3.9 | Yes (11.x–12.x) | Yes | No |
| RELION 3.1 | — (compiled binary) | — | Yes | Yes | No |
| OPUS-TOMO | `opuset` | 3.8 | Yes (11.x) | Yes (≥4× V100) | No |
| PEET | — (bundled MCR) | — | No | No | No |
| emClarity | — (bundled MCR 2020b) | — | Yes (10.x+) | Yes | No |
| I3/ProTomo | — (compiled binary) | — | No | No | No |
| PyTom + AC3D | `pytom_env` | 3.8 | Optional | Optional | No |
| DISCA | `aitom` | 3.8 | Yes | Yes | No |
| HEMNMA-3D | `scipion3` (via plugin) | 3.8 | No | No | Yes |
| TomoFlow | `scipion3` (via plugin) | 3.8 | No | No | Yes |
| MDTOMO | `scipion3` (via plugin) | 3.8 | No | No | Yes |
| TomoNet | `tomonet` | 3.8 | Yes | Yes | No |

---

## Conda Environment Isolation Strategy

Because several packages pin conflicting PyTorch and CUDA versions, never install multiple packages into the same conda environment. Use a strict one-env-per-tool policy:

```bash
# Activate the right environment before working with each tool:
conda activate relion4py    # for RELION Python tools
conda activate opuset       # for OPUS-TOMO
conda activate aitom        # for DISCA
conda activate pytom_env    # for PyTom + AC3D
conda activate scipion3     # for HEMNMA-3D, TomoFlow, MDTOMO
conda activate tomonet      # for TomoNet
```

---

## Standardizing Inputs Across All Packages

For the benchmark, you want to feed each package the **same pre-aligned subtomograms** rather than running full pipelines from raw tilt series. The common interchange format is:

- **Subtomograms:** MRC files (one per particle, or a single stack)
- **Metadata:** RELION 3.1-format STAR file (most packages can read this)
- **Poses:** Euler angles in the STAR file `rlnAngleRot`, `rlnAngleTilt`, `rlnAnglePsi`
- **CTF info:** `rlnDefocusU`, `rlnDefocusV`, `rlnDefocusAngle` per particle

Conversion utilities:
```bash
# RELION star ↔ Dynamo table: use dynamo2relion scripts in the Dynamo package
# RELION star → PyTom XML: built into PyTom
# RELION star → STOPGAP motivelist: use the ww_emClarity or STOPGAP utilities
# RELION star → PEET CSV: use PEET's motl conversion tools or write a short Python parser
```

A minimal Python function to read/write STAR files across tools:
```python
import starfile  # pip install starfile
df = starfile.read("particles.star")
# Manipulate as a pandas DataFrame
starfile.write(df, "converted.star")
```

---

## Troubleshooting Quick Reference

| Symptom | Likely cause | Fix |
|---|---|---|
| `CXXABI_1.3.9 not found` | GCC too old | `module load gcc/11` before compiling RELION |
| `libGL error: swrast` | Missing Mesa drivers | `sudo dnf install mesa-libGL mesa-dri-drivers` |
| `MCR_ROOT not found` | emClarity can't find MCR | Set `LD_LIBRARY_PATH` as shown in emClarity section |
| CUDA/cupy mismatch | Wrong CUDA in conda env | Match `cuda-version=` to output of `nvcc --version` |
| Scipion plugin not found | Plugin not installed | Run `scipion3 installp -p scipion-em-continuousflex` |
| PyTom backend compile fails | Missing FFTW headers | `sudo dnf install fftw-devel` |
| openmpi not found at RELION cmake | MPI not loaded | `module load mpi/openmpi-x86_64` before cmake |

---

## Version Pinning Record

Document exact versions used in your benchmark here (fill in after installation):

| Package | Version / Git hash | CUDA | PyTorch | Notes |
|---|---|---|---|---|
| RELION 4.0 | | | | |
| RELION 3.1 | | | | |
| OPUS-TOMO | | | | |
| PEET | | — | — | |
| emClarity | | | — | |
| I3/ProTomo | | — | — | |
| PyTom | | | | |
| DISCA (aitom) | | | | |
| HEMNMA-3D | | — | — | |
| TomoFlow | | — | — | |
| MDTOMO | | — | — | |
| TomoNet | | | | |

Record `git rev-parse HEAD` for source installs and `conda list` output for each environment. Store these alongside your benchmark results for reproducibility per the Weber et al. (2019) benchmarking guidelines.
