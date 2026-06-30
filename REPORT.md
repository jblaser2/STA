# STA Benchmark — Design Decisions and Methodology Justifications

This document records citation-backed rationale for non-obvious design choices made during the
benchmark. Intended audience: manuscript reviewers and future collaborators who need the *why*
behind a decision, not just the *what*.

---

## Design Decision: Two-Class Injectisome Benchmark (not three)

### Summary

The synthetic T3SS injectisome dataset was originally designed with three classes,
defined by cytosolic sorting-platform axis state: full injectisome (A), basal body
without sorting platform (B), and an intermediate state. Empirical testing showed
the sorting-platform-defining class boundary (A–B, 14 px signal, six-pod C6-star
density) was fundamentally unlearnable even by template-matching on GT-aligned
particles (ARI = 0.034), and this held even at an amplified contrast setting
(AMP = 4.0). The IM-ring-defining boundary (B–C, 19 px, continuous ring) gave a
template-matching ceiling of ARI = 0.558 — a usable hard-tier signal.

We therefore collapsed the design to two classes: class_B (IM ring + outer ring,
n=215) vs. class_C (outer ring only, n=120), plus 80 junk particles.

This is not a retreat from rigor — it is consistent with where the subtomogram
classification field's demonstrated capability currently sits, and we document
that justification here for reviewers.

### Why two classes, not three

**1. The field treats K (number of classes) as a major open problem, not a solved
parameter.** Reviews of subtomogram classification methods explicitly list "the
unknown number of classes" alongside low SNR and incomplete angular sampling as
core unsolved challenges in the field (Bartesaghi-style classification reviews;
see also Chen et al., *Subtomogram classification challenges*). This is a tacit
admission that reliably resolving K ≥ 3 is not yet routine, even before sparse-data
effects are considered.

**2. Classification quality degrades with K even in the much higher-SNR
single-particle (SPA) regime.** SPA particles carry far more signal per copy than
cryoET subtomograms (no missing wedge, no tilt-series dose fractionation penalty,
typically much higher particle counts). Even there, the methodological literature
notes that 3D classification quality "deteriorates significantly as K increases,
because for large K each class is assigned a small number of images and class
assignment therefore becomes more challenging" — and that common practice is to
classify with small K, discard poorly-populated/ambiguous classes, and re-classify
hierarchically rather than solve for many classes simultaneously in one pass. CryoET
subtomograms have strictly worse per-particle SNR than SPA particles, so this
scaling penalty is worse, not better, in our domain.

**3. When ≥3 structural states ARE reported for in-situ assembly intermediates in
the literature, they are typically identified by manual/visual curation across many
tomograms and species, not recovered algorithmically from a single sparse pool via
blind multi-class clustering.** Studies of flagellar motor assembly/disassembly
intermediates (e.g., Beeby and colleagues; Zhao et al. on *Borrelia*) identify
multiple discrete intermediate states, but do so by expert visual sorting of
class averages across large imaging campaigns — not by asking a single automated
classifier to blindly separate k=3+ populations from one sparse dataset. This is
a meaningfully different task than what package-vs-package STA benchmarking asks
software to do unsupervised.

**4. Even well-resourced, methodologically sophisticated efforts on real in-cell
data often settle for a two-way split when more states plausibly exist.** The 2025
Beck/Frydman in-situ TRiC study (Xing et al.) used 3D classification to resolve a
single most-separable axis of heterogeneity in cells — chaperonin assemblies with
one vs. two bound prefoldin domains — despite TRiC's conformational landscape being
considerably richer than a binary split in principle. The practical choice was to
resolve the cleanest two-way signal rather than force a full multi-state
decomposition.

**5. Our own benchmark's empirical results corroborate this independently.** On the
real T4P dataset — a genuine two-class problem — most tested packages (RELION,
PyTom, DISCA, TomoFlow, ProTomo, EMAN2) failed to recover even the two known
conformational states; only Dynamo and PEET succeeded. If two-class separation at
~650 sparse particles is already a stress test that the majority of 3D-input STA
packages fail, asking packages to additionally resolve a third class defined by a
weak, diffuse six-pod density (sorting platform, ARI ceiling 0.034 even via
template matching) tests a regime past the field's currently demonstrated ceiling.
A three-class design here would likely produce a uniformly flat failure floor
across all packages, which destroys the benchmark's discriminative power between
methods — the opposite of what a comparative benchmark needs.

### What we keep from the three-class effort

The `motor_easy` synthetic dataset (3 ground-truth classes, ~30 Å structural
differences, template-matching baseline ARI = 0.289) demonstrates that 3-class
problems ARE sometimes resolvable when the structural differences are large and
discrete (whole substructure present/absent, e.g., C-ring removal). The injectisome
sorting platform's failure at the same exercise — diffuse, low-contrast,
multi-pod geometry, 14 px feature size — is not a contradiction of that result.
It is a second, complementary data point mapping the boundary of feasibility:
**large discrete structural removal is learnable; small diffuse multi-component
signal is not, even with synthetic ground truth and amplified contrast.** This
boundary-mapping result is itself a citable contribution of the benchmark and is
worth stating explicitly in the manuscript discussion, framed as a design finding
rather than a limitation.

### Anticipated reviewer pushback and response

- *"Why not just try harder to resolve 3 classes (more iterations, better priors,
  alternate algorithms)?"* — We did stress-test this (AMP=4.0 amplification) and
  the sorting-platform signal remained unlearnable even under idealized
  template-matching on GT-aligned particles, which represents a near-ceiling
  upper bound on any package's real-world performance. If template matching with
  known ground-truth alignment cannot separate the classes, no blind
  classification package realistically will either.
- *"Doesn't dropping to 2 classes make the benchmark easier than necessary?"* — No;
  the B–C boundary retains a non-trivial ceiling (ARI = 0.558), keeping it a
  genuine hard-tier benchmark, while remaining within the range of problems the
  field has shown can sometimes be solved (cf. T4P real-data 2-class precedent
  within this same project).
