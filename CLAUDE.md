# STA Benchmarking Project — Claude Code Context

## Project Overview
CryoET STA conformational heterogeneity classification benchmark. Goal: first systematic benchmark
using realistic in-situ CryoET datasets across all major 3D-input classification packages.
Scientific context: membrane-embedded complexes (T4P, flagellar motor), sparse particle counts
(500–1000), 3D subvolume input, no reliable ground truth on real data.

## People
- **Josh Blaser** — undergrad, primary researcher (user of this config)
- **Eben** — undergrad partner, works on same GitHub repo from his own machine; currently getting
  familiar with package setup and running classifications on existing data
- **Stefano** — postdoc expert in CryoET field, consulted for scientific advice and manuscript review
- **Braxton Owens** — PhD student, also provides guidance

## Dataset
- **Real:** 672 hand-picked, prealigned 80³ subtomograms of T4P (Vibrio), no reliable ground truth
- **Synthetic (planned):** 2 datasets (3-class and 4-class), conformational heterogeneity,
  large (~30Å) and small (~10Å) structural differences, matched SNR, simulated missing wedge,
  imbalanced class sizes

## Packages Under Evaluation (3D input only)
RELION 3.1–4.0, STOPGAP, OPUS-TOMO, Dynamo, PEET, MDTOMO, TomoFlow, I3/ProTomo, EMAN2,
emClarity, PyTom, DISCA, HEMNMA-3D, AC3D, TomoNet

## Directory Structure
```
STA/
├── subtomos_mrc/        # 672 individual .mrc subtomograms (gitignored)
├── outputs/             # Per-package classification outputs
│   └── relion/
├── scripts/
│   ├── data_prep/       # Input conversion scripts per package
│   └── markdown_instructions/  # Per-package usage guides (RELION, DYNAMO, STOPGAP, etc.)
├── dynamo/              # Dynamo workspace
├── peet/                # PEET project files and guides
├── stopgap/             # STOPGAP scripts and compiled binaries
├── PyTom/               # PyTom scripts
├── eman2/               # EMAN2 workspace
├── etsimulation/        # Synthetic data generation research/scripts
├── README.md            # Full project overview and evaluation plan
└── Package_installation.md  # Installation guide per package (RHEL 10)
```

## Key Workflow Conventions
- Master particle index: `outputs/master_particles.{csv,star,json}` — all packages index from here
- Standardized preprocessing: normalize → identical voxel size → identical box size → feed to each package
- Run classifications at k=2, 3, and 4 for every package
- Large files (`.mrc`, `.star`, `.hdf`, `.h5`, archives) are gitignored — only scripts and docs commit
- Package-specific conda envs: `eman2`, `etsim`, `pytom_env`, `relion-5.0` (on Josh's machine)

## Evaluation Framework (summary)
| Metric group | Weight |
|---|---|
| Stability (bootstrap 80%×20, 5-fold CV, noise perturbation) | 35% |
| Internal validity (silhouette, Davies-Bouldin, Calinski-Harabasz) | 25% |
| Cross-package agreement (pairwise ARI/NMI, co-occurrence matrix) | 20% |
| FSC resolution gain (gold-standard FSC per class) | 20% |

## Current Focus
*(Update this section as the project progresses — to be filled in by Josh/Eben)*
