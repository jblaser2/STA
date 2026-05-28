# STA
Creating a benchmark evaluation of sub-tomogram classification packages for CryoET.

# Project Overview

# Benchmark Dataset for Subtomogram Averaging Particle Conformational Heterogeneity Classification Packages
### Using Sparse 3D Data of Membrane-Embedded Complexes

---

## Background

Cryo-EM has two important applications in determining macromolecular structure. One is called **Single Particle Analysis (SPA)**, and the other is **CryoET with Subtomogram Averaging (STA)**.

### Single Particle Analysis (SPA)

SPA has been around longer and is a method that biochemically purifies the target complex. Essentially, a certain structure within a certain bacteria cell is isolated using special chemicals so that the solution that is imaged just contains billions to trillions of the exact same complex. This solution is frozen and then imaged with an electron microscope. The complexes will all be at different orientations in the frozen solution. When imaged with the electron microscope, the images received are all 2D. Each instance of the particle at different orientations can be thought of as a 2D projection of the 3D object. The 2D projection images are aligned and averaged to create high resolution 3D reconstructions of the target complex.

This method is great and good at what it does. However, there are certain cellular complexes that cannot be isolated, making SPA fall short in its ability to determine the macromolecular structure. This is where CryoET and STA comes in.

### CryoET and Subtomogram Averaging (STA)

Complexes like the **Flagellar Motor** or **Type IV Pilus** are *membrane-embedded*, meaning that they are a structure that lives within the membrane of the cell, rather than just floating around in the cytoplasm or extracellular space. In other words, they are anchored to part of the cell. Trying to isolate the complex would break apart the cell membrane and the complex would fall apart. Since they cannot be isolated, a method called Cryogenic Electron Tomography is used to image the entire cell, with the target complex still in its native place within it. Rather than creating a solution with billions of copies of the target complex, a solution containing entire cells is frozen and then imaged in the microscope. Instead of having billions of particles each at different orientations, the sample is tilted back and forth (usually about ±60°) to allow for 3D reconstruction of the target complex. The 2D images collected are recombined and aligned to form a 3D image called a **tomogram**. Now, the cell basically exists in three-dimensional space on the computer just as it did in real life. (It is not entirely the same, as there are large amounts of detail lost due to the missing wedge, the fact that the wedge is split into slices, and the CTF). Tomograms typically have the file format `.mrc` which stands for Medical Research Council, UK, where it was developed.

From here, the tomogram is visualized using programs that can open 3D images, and scientists or ML algorithms locate the complex of interest within the volume. Once the complex has been located, it is 'aligned' so that it faces a certain direction and extracted as a subvolume. This subvolume is typically called a **subtomogram**. This process is repeated hundreds of times so that there is enough data to resolve an electron density map of the structure of interest. When there are at least a few hundred particles extracted and aligned as subtomograms, they are classified (separated into groups based on their phase of life/construction) and averaged. Hence the term subtomogram averaging.

The classification step is something that is not very typical in SPA because normally all of the complexes are the same. However, in situ imaging means that we will see structures in all different phases of life. In order to get the highest resolution of map when the subtomograms are averaged, the different phases of the complex need to be separated and sorted into their distinct classes. This is a very important step in resolving the macromolecular structure of the complex of interest.

---

## Project Goal

Many packages and softwares using different classification methods and algorithms have been developed and are currently in-use by researchers. However, no benchmarking has been done across all these packages using the same dataset. This will be the aim of this project. Create a benchmarking dataset consisting of real and synthetic subtomogram data and then use it to benchmark the current subtomogram classification algorithms used in several packages. This is done with a focus specifically on sparse data of membrane embedded complexes and using 3D data as input for the classification.

---

## What Makes This Project Unique

So far, some informal benchmarking has been done on STA classification algorithms. Many of the datasets used in such benchmarking are focused on complexes whose macromolecular structure can be resolved using SPA (e.g., 80S ribosomes). It is strange that a dataset that doesn't need STA would be used to evaluate STA classification algorithms, but it also makes sense as doing so provides a more reliable ground truth. We want to evaluate STA classification algorithms using datasets that are more realistic to the field. CryoET is defined by complexes of interest that are typically large, unable to lyse, membrane-embedded, or asymmetric. Focusing on membrane-embedded complexes is something specific and unique to CryoET.

In addition to this, previous informal benchmarking datasets contain on the order of 10,000 particles. For most large complexes that STA is used to resolve, a realistic number of particles is a whole order of magnitude smaller (500–1000 particles). This significantly changes STA and classification as resolution and class separation depends heavily on the number of particles collected.

Many packages have switched their focus to performing classification on 2D particle-images rather than 3D subtomograms. The use of 2D workflows increases computational efficiency and minimizes interpolation errors. However, in order to isolate this project to focusing on the classification step, we will focus just on the packages that use 3D data as input for their classifications. We recognize that omitting the packages that perform classification on 2D data means that just a subset of the existing classification algorithms are being tested. A companion 2D-input benchmark would be a natural extension of this project.

---

## Making the Dataset

### Real Data

Currently we have a dataset of 672 hand-picked and prealigned 80³ subtomograms of the Type IV Pilus (T4P) from Vibrio bacteria tomograms. This will be one of our real datasets that we use to test the classification algorithms. This specific dataset does not have resolvable ground truth at its resolution. It is unclear as to whether this dataset will exhibit discrete classes or a more continuous behavior. We leave this explicitly as an open question and plan for the possibility that the classes are not cleanly discrete.

The other should be a complex that is more clearly discrete. Something like flagellar motor assembly intermediates would be perfect.

Each of the packages are usually part of a larger pipeline, and it is difficult to isolate this conformational heterogeneity classification step. On top of that, it is difficult to have reliable ground truth for subtomogram particle classes since researchers cannot tell a particle's class from looking at an individual subtomogram. Using real data, we will not have a perfect ground truth as to which particle belongs to which class. We aren't even completely sure how many distinct classes there should be in the given dataset. This makes creating a benchmark dataset very difficult. We will have to come up with ways to reliably compare the classification results of the different packages without the ground truth.

On top of the usage of unclear but real subtomogram data, we will create a synthetic dataset so that we will have a more reliable ground-truth. This is great because it has reliable ground-truth, but not so great because it is just not that realistic. A combination of evaluation based on the real dataset and the synthetic dataset should give the most credibility to this benchmarking process amongst the critics in the field.

### Synthetic Data

This is the tentative plan with need for some corrective feedback:

- 2 datasets, one with 3 classes, one with 4
- Distinctions between classes are conformational heterogeneity
- One dataset has a large structural difference (~30 Å) between classes and the other has a smaller one (~10 Å). The purpose of doing this is to find a sweet spot where some classification algorithms work better than others, rather than all of them failing or succeeding
- SNR will be matched to the real T4P data's SNR
- We will simulate the missing wedge in our synthetic data. This is important to obtain realisticity of our synthetic subtomogram particles
- Class sizes will be imbalanced to be as realistic as possible

---

## Which Packages to Test?

In order to keep this benchmark focused and feasible, we are evaluating only packages that perform classification on 3D data. Discrete classification will be done since that is necessary for STA. For packages that perform continuous classification, we will use the same clustering method to discretize the classes. Really the only requirement for packages on this dataset is that they can take aligned 3D subvolumes as input. Here are the packages found that fit this description:

- RELION 3.1–4.0
- STOPGAP
- OPUS-TOMO
- Dynamo
- PEET
- MDTOMO
- TomoFlow
- I3/ProTomo
- EMAN2
- emClarity
- PyTom
- DISCA
- HEMNMA-3D
- AC3D
- TomoNet

---

## Evaluating the Results

We will have to be creative and consistent when evaluating the results of each respective classification package on the real data. Here is a tentative plan that is pretty staple for ML engineers:

### 1. Data Preparation
Ensure a level playing field: standardise CTF correction, mask radius, angular sampling, and normalisation so differences in scores reflect classification quality, not preprocessing discrepancies.

### 2. Synthetic Data Generation
Also have synthetic data with known ground truths.

### 3. Classification Matrix
Run all 8–10 packages at k=2, 3, and 4. This gives 24–30 output label sets on your real data, plus the same on synthetic. Store label assignments per particle — you need these for all downstream agreement calculations.

### 4. Internal Validity Indices
Compute silhouette, Davies-Bouldin, and Calinski-Harabasz on each output. For sparse data (600–1000 particles), a key nuance: compute these in the package's own latent/embedding space rather than raw voxel space, since voxels are extremely high-dimensional and distances become unreliable (curse of dimensionality). If a package gives you access to its latent coordinates (e.g. PCA/VAE embeddings in RELION, cryoDRGN), use those.

For packages that don't expose their latent space in a useable format: compute per-particle cross-correlations against each class average, producing an N×k matrix used as a low-dimensional coordinate for silhouette calculations.

### 5. Stability Analysis *(the most important stage for sparse data)*

With only 600–1000 particles, stability testing deserves extra weight:

- **Bootstrap** (80% subsets × 20 runs): compute Jaccard similarity of the resulting clusters across runs. Threshold ≥ 0.75 is commonly used; < 0.6 suggests the classification is noise-driven.
- **5-fold cross-validation:** hold out 20% of particles, classify the 80%, assign held-out particles by nearest-centroid, measure ARI between held-out assignments and full-dataset assignments.
- **Noise perturbation:** add Gaussian noise at 0.5σ and 1σ to the particles, re-classify, measure label flip rate. Biologically meaningful classes should be robust to mild additional noise.

### 6. Cross-Package Agreement

Build a consensus co-occurrence matrix: an N×N matrix (N = number of particles) where each cell counts how many packages placed those two particles in the same class. Dense off-diagonal blocks reveal classes that are genuinely robust across methods. Then:

- Compute pairwise ARI/NMI between all package outputs at the same k — packages that strongly agree are converging on real structure.
- Use your synthetic calibration ARI as a reference anchor: if two packages agree at ARI=0.85 on synthetic data but only 0.4 on real data, that gap is scientifically meaningful.

### 7. Resolution Proxy Validation
This is the domain-specific ground truth proxy. For your top 2–3 candidate (package, k) combinations, run gold-standard FSC on each class separately and compare against the unsplit full dataset. A good classification should yield per-class FSC curves that extend to higher resolution than the mixed map. This is the closest thing to a ground truth signal you can get in CryoET and should inform the final decision heavily.

### 8. Composite Scoring

Aggregate using rank-based aggregation (Borda count or Kemeny-Young) rather than raw score averaging, since the scales are incommensurable across metrics.

| Metric group | Weight | Rationale |
|---|---|---|
| Stability (bootstrap + CV + noise) | 35% | Sparse data → stability is paramount |
| Internal validity indices | 25% | Standard but complemented by others |
| Cross-package agreement | 20% | Multi-method consensus is reliable signal |
| FSC resolution gain | 20% | The biological payoff metric |

> **Note:** If internal validity scores are all clustered close together (which happens with sparse data) and stability scores vary widely, the weights you've assigned may not translate into the ranking behavior you expect. Will report individual metric rankings alongside the composite.

> **Expert review needed** before finalizing and executing the evaluation plan. The scoring framework, metric weights, and statistical thresholds should be reviewed by someone with expertise in algorithm performance evaluation.

---

## Remaining Questions

- What scope does the synthetic data need to cover? How many classes of each particle type? How many different particle types? My gut says we do one of 3 classes and another of 4 classes, making sure the complexes are different sizes.
- What do we do with particles that don't fit into the main classes? Throw them out? Focus on them? They could be of particular interest but will also mess up the averaging of the main classes.
- How do we standardize correction for the missing wedge? Just ignore it? Maybe ignore just for the real data? This is arguably the dominant confound in subtomogram classification. The missing wedge creates directional artifacts that can be mistaken for structural differences by classification algorithms. Any benchmarking that doesn't control for missing wedge effects — especially when particles have preferred orientations — will be misleading. The synthetic data generation must include realistic missing wedge simulation. Tools like InSilicoTEM, Parakeet, or the tomoDRGN simulation framework can do this.
- What do we do about particles that exhibit continuous phase states? (e.g. T4P extension/retraction cycles)
- For the packages that classify continuously, how should we discretize the classes for STA? Each package seems to handle the k parameter (# of classes) differently. We will need to be careful to make this as streamlined as possible.

---

## Schedule

| Phase | Time | Scope |
|---|---|---|
| Get project feedback & finish the lit review and writeup | 1 week | Send to Stefano, write on Overleaf, get critiques and implement them |
| Get all of the packages up and running | 2–3 weeks | Will be hard but Claude is our friend here |
| Generate synthetic data | 1 week | etSimulations — should be easy? |
| Standardized Input Preparation | 1 week | Common preprocessing pipeline to feed all of the packages |
| Run all of the packages | 2 weeks | Possibly reach out to all package developers and get their input |
| Scoring analysis | 1–2 weeks | Use scoring metric in table above |
| Writing | Parallel | |
