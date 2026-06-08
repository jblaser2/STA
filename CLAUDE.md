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
10 active: RELION, STOPGAP, OPUS-TOMO, Dynamo, PEET, TomoFlow, I3/ProTomo, EMAN2, PyTom, DISCA.
Not tested (with reasons): see `docs/excluded-packages.md`.

## Directory Structure
```
STA/
├── packages/            # All 10 actively-tested classification packages
│   ├── README.md        # Master progress table (all packages × all datasets)
│   ├── dynamo/          # Dynamo workspace + README.md
│   ├── peet/            # PEET project files + README.md
│   ├── relion/          # RELION scripts + README.md
│   ├── PyTom/           # PyTom scripts + README.md
│   ├── eman2/           # EMAN2 workspace + README.md
│   ├── opusTomo/        # OPUS-TOMO scripts + README.md
│   ├── STOPGAP/         # STOPGAP source + pipeline + README.md
│   ├── disca/           # DISCA scripts + README.md
│   ├── tomoflow/        # TomoFlow scripts + README.md
│   └── protomo/         # ProTomo scripts + README.md
├── data/                # Dataset files and QC artifacts
│   ├── T4P_subtomos/    # 672 T4P subtomograms (local only, gitignored)
│   ├── T4P_mask/        # Cylindrical classification mask
│   ├── alignment_review/# T4P particle alignment QC
│   ├── masked_average/  # Masked averaging experiments
│   └── few_sta_test/    # Resolution-scaling validation (archived)
├── synthetic/           # Synthetic data pipeline docs
│   └── etsimulation/    # ETSimulations pipeline docs and scripts
├── scripts/
│   ├── data_prep/       # Input conversion scripts per package
│   └── eval/            # Scoring tools (ARI/AMI/V-measure, FSC)
├── outputs/             # Large binary run outputs (gitignored), organized by package
├── results/             # Aggregated scoring CSVs + figures (committed)
├── docs/                # Background documents and installation guides
│   ├── excluded-packages.md    # Packages evaluated but not tested
│   ├── Package_installation.md # Installation guide per package (RHEL 10)
│   ├── benchmarkIdeas.md       # Evaluation framework design
│   └── Relion-algorithm-use.md # RELION algorithm notes
├── README.md            # Full project overview and evaluation plan
└── STATUS.md            # Single source of truth for project state
```

## Key Workflow Conventions
- Master particle index: `outputs/master_particles.{csv,star,json}` — all packages index from here
- Standardized preprocessing: normalize → identical voxel size → identical box size → feed to each package
- Run classifications at k=2, 3, and 4 for every package
- Large files (`.mrc`, `.star`, `.hdf`, `.h5`, archives) are gitignored — only scripts and docs commit
- Package-specific conda envs: `eman2`, `etsim`, `pytom_env`, `relion-5.0` (on Josh's machine)

## Package README Protocol

**After any STATUS.md update that touches a package result, also update:**
1. `packages/README.md` — update that package's row in the progress matrix
2. `packages/<pkg>/README.md` — update the results table and next steps section

This applies to: run completions, new ARI scores, config changes, status changes (⬜ → ✅),
or any result that would change what appears in STATUS.md's package matrix row.

The `/handoff` skill (`.claude/commands/handoff.md`) includes this as an explicit checklist
step — do not skip it when running `/handoff`.

**Figure gallery protocol (added 2026-06-08):** `packages/README.md` has a visual figures
gallery embedded in each dataset's progress table — class-average thumbnails and (for
motor_easy) confusion matrix thumbnails per package row. When a new classification run
completes or an existing result improves:

- **Class-average panel:** generate a new PNG using `scripts/eval/gen_class_avg_panels.py`
  with the package's class-average MRC files, save to `packages/figures/<dataset>/`,
  and update the "Class Avgs" cell in the table.
- **Confusion matrix (motor_easy only):** if a better confusion matrix PNG is generated,
  update the "Best Confusion" cell to point to it.
- **Cross-package correlation (T4P):** re-run `scripts/eval/gen_cross_pkg_correlation.py`
  if a new package's T4P assignment CSV is added to `results/` — this regenerates
  `packages/figures/T4P/cross_pkg_correlation.png`.

Cells currently showing `_(pending)_` need local MRC class-average files; fill them with
`gen_class_avg_panels.py` as each package's class averages become available.

## Evaluation Framework (summary)
| Metric group | Weight |
|---|---|
| Stability (bootstrap 80%×20, 5-fold CV, noise perturbation) | 35% |
| Internal validity (silhouette, Davies-Bouldin, Calinski-Harabasz) | 25% |
| Cross-package agreement (pairwise ARI/NMI, co-occurrence matrix) | 20% |
| FSC resolution gain (gold-standard FSC per class) | 20% |

## Cross-Session Workflow (read this every session)
- **`STATUS.md` is the single source of truth** for project state — what's installed, what's run,
  what's blocked. Read it first; keep it current. Do NOT track status in memory files.
- **Start** each session with `/status` (briefs you from STATUS.md + latest session-log).
- **End** each session with `/handoff` (updates STATUS.md, writes a `.session-log/` entry, updates
  durable memory, stages changes).
- **Pick up a package** with `/pkg <name>` (loads that package's row + guide + memory).
- **One workstream per session** — don't blend a package install with analysis of another.
- `.session-log/YYYY-MM-DD-<topic>.md` holds dated handoff notes (committed, small markdown).
- **Memory role split:** memory = *durable knowledge* (install quirks, fixed bugs, run commands);
  STATUS.md = *current status*. When you learn a durable fact, save it to memory; when state
  changes, update STATUS.md.

## Config & Launch
- Launch Claude Code from **inside `~/Research/STA`** so this CLAUDE.md, `.claude/commands/`, and
  `.claude/settings.json` all apply (and Eben inherits them via git). Large data and some package
  source live in the parent `~/Research/` (reachable by absolute path; add it as an additional
  working directory if needed).
- Shared permissions: `.claude/settings.json`. Machine-specific: `.claude/settings.local.json`
  (gitignored).
