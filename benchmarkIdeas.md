# Benchmark Design Ideas — STA Conformational Heterogeneity Classification

> Working document. Discusses how we *should* score the 15 packages under evaluation. Complements
> the evaluation plan already laid out in `README.md` §8 (Stability 35% / Internal validity 25% /
> Cross-package agreement 20% / FSC resolution gain 20%). Per direction, the README framework is
> treated as a constraint to preserve; serious concerns are raised here rather than by editing the
> README. Author: Claude with E. Lonsdale, 2026-06-02.

---

## 0. What problem this document is solving

User-stated open question (Eben, 2026-06-02): we know the T4P set has two phases (Stefano), so
F-beta of per-particle labels against ground truth is one option, but it has three problems:

1. **Goal mismatch.** F-beta against discrete labels does not directly measure downstream STA
   resolution, which is the actual scientific payoff.
2. **No regime resolution.** A single agreement score does not tell us *when* one algorithm beats
   another — different methods are likely to win in different data regimes (sparse vs dense,
   conformational vs compositional, large vs small structural difference, etc.).
3. **Not extensible.** Most real datasets in this field have no reliable ground truth; an
   F-beta-only protocol cannot be transported to them.

This document surveys the metrics and aggregation strategies used in the cryo-EM and
clustering-evaluation literature, maps them onto our four pillars, addresses each of the three
concerns explicitly, and proposes concrete output formats.

---

## 1. Four lenses for "best classifier"

The user-confirmed goal is a *blend* of (a) downstream STA resolution, (b) match to ground truth
when available, (c) reproducibility / robustness. To express that, we structure the benchmark
around four lenses; the four README pillars are a special case of this taxonomy.

| Lens | Question it answers | GT required? | Maps to README pillar |
|---|---|---|---|
| **A. External validity** | Does the partition match known truth? | yes | (none — not in README; added under "external validation" below) |
| **B. Downstream resolution** | Does classifying improve per-class STA resolution? | no¹ | FSC resolution gain (20%) |
| **C. Stability / robustness** | Is the partition reproducible under resampling, noise, reruns? | no | Stability (35%) + Internal validity (25%) |
| **D. Cross-method consensus** | Do independent algorithms agree on the same particle groupings? | no | Cross-package agreement (20%) |

¹ Lens B uses *internal* gold-standard FSC (independent half-set per class) and does not require
external GT; if synthetic atomic models exist, map-to-model FSC can also be used.

Each lens is independently scoreable; pillar weights from README are applied at the aggregation
step (Section 6). Single-pillar fragility is mitigated by always reporting per-pillar numbers
alongside the composite, per the README §8 note about clustered internal validity scores.

---

## 2. Metric catalog (cited)

Below: a vetted shortlist for each lens, with the canonical reference, why it's useful for our
setting, and a caveat.

### 2.1 Lens A — External validation (vs known labels)

Used on (i) synthetic data (true labels exist) and (ii) real T4P with Dynamo's two pili-phase
partition treated as *de facto* GT (with a "soft GT" caveat — see §4.1).

| Metric | Ref | What it captures | Notes |
|---|---|---|---|
| Adjusted Rand Index (ARI) | Hubert & Arabie 1985 | Pair-counting agreement, chance-adjusted | Standard. Inflates for many clusters; OK at our k≤4. |
| Adjusted Mutual Information (AMI) | Vinh, Epps & Bailey 2010 | Info-theoretic, chance-adjusted | Recommended when ref clustering is **unbalanced** (Romano et al. 2016) — relevant for real T4P. |
| Normalized MI (NMI) | (legacy) | Info-theoretic, not chance-adjusted | Report for continuity with prior cryoBench-style papers; rely on AMI. |
| V-measure (homogeneity / completeness) | Rosenberg & Hirschberg 2007 | Each cluster pure / each class fully captured | Useful for diagnosing whether a method *splits* one true class or *merges* two. |
| F-beta after Hungarian matching | Munkres 1957; Steinley 2004 | Per-class precision/recall after label-permutation alignment | Resolves the label-permutation issue F-beta has on raw cluster IDs. |
| Class purity / completeness (per class) | Manning et al. 2008 | Diagnostic split per ground-truth class | Lets us report "did the method find phase A but not phase B?" |
| Information Imbalance Δ | Glielmo et al. 2022 (used by CryoBench) | Asymmetric info content of one embedding vs another | Only if package exposes a latent space. |
| Neighborhood similarity p_MN | CryoBench (Jeon et al. 2024) | % of shared k-nearest-neighbors between latent and GT embedding | Latent-space methods only (OPUS-TOMO, etc.). |

**Why not bare F-beta** (the user's instinct): without Hungarian matching, F-beta depends on
arbitrary cluster numbering. With matching, F-beta becomes a legitimate per-class precision/recall
report, but it still suffers when the algorithm's k differs from |GT classes| — ARI/AMI tolerate
that better. *Recommendation:* report F1 after Hungarian as a per-class diagnostic, but use AMI
(primary) + ARI (secondary) as scalar scores.

### 2.2 Lens B — Downstream STA resolution (the biological payoff)

| Metric | Ref | What it captures | Notes |
|---|---|---|---|
| Gold-standard FSC @ 0.143 | Rosenthal & Henderson 2003 | Per-class half-set resolution | Industry standard. Requires independent half-set refinement *within each class*. |
| AUC-FSC | CryoBench (Jeon et al. 2024) | Area under per-class FSC curve | Single scalar per class, robust to noisy tail. Used widely in CryoBench. |
| Per-Conformation FSC | CryoBench | FSC of recovered vs GT volume per conformation | Synthetic only (needs GT volume). |
| Sample FSC / Per-Image FSC | CryoBench | FSC after K-means in latent space → decode centroid → compare to GT | For methods with a latent space; flexible to k mismatch. |
| Resolution gain Δres = res(class) − res(unsplit) | Common practice; tracked in `relion_class_report.py` | Improvement over not classifying | Our *primary downstream score* for real data. |
| Mask-corrected vs unmasked FSC | Common practice | Detects mask-induced inflation | Always report both. |
| Per-class B-factor (Guinier) | Rosenthal & Henderson 2003 | Map sharpness per class | Useful when FSC is noisy at low N. |
| Map-to-model FSC | Lawson et al. 2021 | Map vs known atomic model | Synthetic only, if atomic models are released. |
| Local resolution (ResMap / blocres) | Kucukelbir et al. 2014 | Spatial variation in resolution per class | Diagnostic — can show whether classification cleans up a *region* of the map. |

**Critical caveat for sparse data.** With 500–1000 particles split into k classes, half-sets are
∼125–500 particles. FSC at that count is noisy; AUC-FSC and B-factor are more stable summaries.
Use them as the headline numbers.

**Critical caveat re T4P preferred orientation.** Membrane-embedded complexes sit at preferred
poses; this can both inflate FSC (Penczek 2010) and bias per-class resolution comparisons. Report
sphericity (Tan et al. 2017) alongside resolution.

### 2.3 Lens C — Stability / robustness

| Metric | Ref | What it captures | Notes |
|---|---|---|---|
| Bootstrap clusterwise Jaccard | Hennig 2007 (`fpc::clusterboot`) | Per-cluster stability under 80% resampling | Thresholds: ≥0.85 highly stable, ≥0.75 valid, ≤0.6 noise. Our 35% pillar's anchor. |
| Consensus matrix + ΔCDF | Monti et al. 2003 | Pairwise co-clustering frequency; choice of k via CDF area gain | Good complement; also helps pick k objectively. |
| 5-fold CV with nearest-centroid assignment | Common practice | Held-out particle reassignment vs full-set assignment, ARI | README §5 recipe; cheap if package supports prediction; otherwise needs re-fit. |
| Noise perturbation (0.5σ, 1σ Gaussian) | Domain heuristic | Label flip rate under added noise | Mild noise should not flip biologically real classes. |
| Particle-count titration | Custom | Re-cluster at 250/500/672 particles, measure ARI vs full | Tests whether discovered structure is sparse-data-robust. |
| Multi-seed agreement | Custom | Same algorithm, different RNG seeds, pairwise ARI | Fast version of bootstrap when re-fits are cheap. |
| Internal validity (Silhouette, DB, CH, Dunn) | Rousseeuw 1987; Davies & Bouldin 1979; Caliński & Harabasz 1974; Dunn 1974 | Geometry of clusters in embedding | Already in README pillar. **Compute in latent space, not voxel space** (curse of dim — see §7.2). |

**Recommendation.** Use Hennig 2007 clusterboot as the scalar stability score (per-cluster Jaccard
averaged then weighted by cluster size). Use Monti consensus matrices as a visual / k-selection
companion. Note: stability ≠ correctness; combine with Lens A or B before drawing conclusions
(Hennig 2007 §6 explicitly warns about this).

### 2.4 Lens D — Cross-method consensus

| Metric | Ref | What it captures | Notes |
|---|---|---|---|
| Pairwise ARI/AMI heatmap | Strehl & Ghosh 2002 | All-pairs algorithmic agreement at fixed k | Off-diagonal blocks reveal robust groupings. |
| Co-occurrence (consensus) matrix N×N | Strehl & Ghosh 2002; Fred & Jain 2005 | Vote-based "how often do packages cluster particles together?" | Threshold to identify robust *core* groups; remainder is the contested set. |
| Synthetic-ARI anchor | Custom | Use synthetic-data ARI as the "max attainable agreement" anchor when reading real-data ARI | E.g., "packages agree at 0.85 on synthetic but 0.4 on real" is a meaningful gap. |

**Why this is the main extensibility tool.** Cross-package agreement is the most defensible
GT-free signal in the absence of resolution gain — but it shares failure modes (e.g., if every
package locks onto the same alignment artifact, consensus is spurious). Always pair with Lens B.

---

## 3. Direct answers to the three concerns

### 3.1 "F-beta vs GT does not address downstream STA resolution"
Make Lens B (per-class gold-standard FSC, AUC-FSC, resolution-gain over unsplit) a co-equal
pillar. Report Δres = res(class) − res(unsplit) as the *headline number* for the real data — this
is the metric that matches the scientific question ("does classification actually help?"). On the
T4P set this answers Stefano's deeper question better than any agreement score: even a method
that disagrees with Dynamo's labels can still be a win if its classes resolve to higher
resolution.

### 3.2 "F-beta does not reveal which methods win in which regimes"
Treat algorithm performance as a *function of data regime* and characterize that function
explicitly. Concretely: build a regime grid (Section 5C) populated by synthetic-data sweeps, plus
a single real-data anchor point. Per cell, record best-performing package; aggregate across the
grid to get a regime map.

### 3.3 "Not extensible to GT-less datasets"
Lenses B (FSC), C (stability), and D (cross-method consensus) all work without GT. The protocol
can therefore be transported to flagellar motor data, EMPIAR tomograms, or new in-house sets
without modification. F-beta / ARI / AMI can be optionally added when GT is available, but the
benchmark does not depend on them.

---

## 4. Per-dataset application

### 4.1 Real-data track (T4P, n=672, "soft GT")

- **GT source:** Dynamo's two-class partition (per Stefano, 2026-06-01), treated as the *de facto*
  reference. Caveat: Dynamo could be wrong; report results both with and without using this label
  set, and disclose it as soft GT in the write-up.
- **Score every package at k=2, 3, 4** per README §3.
- **Run Lens A** against Dynamo labels: AMI (primary), ARI (secondary), F1-after-Hungarian
  (per-class diagnostic). The "shared failure" finding from STATUS.md (RELION/PyTom/Protomo/DISCA/
  TomoFlow/OPUS-TOMO all missing the two phases) is the headline result regardless of metric
  choice.
- **Run Lens B** per-class gold-standard FSC and AUC-FSC. Report Δres as headline.
- **Run Lens C** Hennig clusterboot (80%×20 bootstrap), 5-fold CV, noise perturbation, multi-seed.
- **Run Lens D** pairwise ARI heatmap across all packages; co-occurrence matrix.
- **Reporting:** one master CSV `outputs/benchmark/labels_matrix.csv` with rows = particle ID and
  columns = (package, k); per-pillar table; composite ranking.

### 4.2 Synthetic-data track (planned 3-class and 4-class)

- **Hard GT** — atomic models, density maps, labels, poses all known.
- **Two condition sweeps already planned in README:**
  (a) Class-distance: ~30 Å vs ~10 Å structural difference.
  (b) SNR matched to T4P.
- **Additional sweeps recommended for the regime map:**
  (c) Particle count: 250 / 500 / 750 / 1000 — sweet-spot identification.
  (d) Class imbalance ratio: balanced vs realistic (e.g., 70/20/10).
  (e) Missing-wedge severity (if controllable in the simulator).
- **Run all four lenses** with the addition of:
  - Per-Conformation FSC vs GT map (CryoBench-style)
  - Map-to-model FSC if atomic models are exported
  - Information Imbalance Δ and p_MN for latent-space methods
- **Use synthetic ARI as the anchor** when interpreting real-data ARI (cf. README §6).

---

## 5. Output formats (the "what do we hand the reader?" question)

Per direction, headline output must be a **numeric score**, with a regime map as an attractive
second option. Four concrete formats are below — recommendation: ship **B + C together** (B is the
core deliverable; C is the high-value differentiator we should target if synthetic sweeps permit).

### Option A: Single composite scalar per package

- Z-score each metric within metric-family, then weighted average via the README weights
  (Stability 35% / Internal 25% / Cross 20% / FSC 20%).
- Or rank-aggregate via **Borda count** (Borda 1781) — fast, robust to incommensurable scales
  (Lin 2010; Hadjar 2024).
- **Pros:** simplest possible "winner" output.
- **Cons:** hides regime variation, which the user explicitly flagged as important.

### Option B (RECOMMENDED): Multi-pillar profile + composite

- Per package: a 4-axis radar (one axis per lens) showing per-lens normalized score, plus the
  composite scalar from Option A.
- **Pros:** preserves the README weights, surfaces per-pillar strengths and weaknesses, easy to
  read. Honest about the README §8 note that pillars can be highly correlated for sparse data.
- **Cons:** still aggregates over data regimes.

### Option C: Regime map / heatmap

- Rows = packages; columns = data regimes (sparse / dense, large-Δ / small-Δ, balanced / imbalanced,
  conformational / compositional). Cell value = top pillar score (or "winner" label).
- Populated from synthetic-data sweeps. Real T4P is one column ("real, sparse, conformational,
  unknown imbalance").
- **Pros:** directly answers "which algorithm works when?" — the highest-leverage scientific
  output of the benchmark.
- **Cons:** needs many synthetic conditions to populate; sparse with 2 planned synthetic sets.
  Requires generating more synthetic sweeps than currently scoped.

### Option D: Pareto-front per pillar pair

- 2D scatter plots: e.g., Stability vs Resolution-gain, ARI vs Stability. Highlight the
  Pareto-optimal packages on each pair.
- **Pros:** honest about no-single-winner outcomes (Wolpert & Macready 1997 NFL — no algorithm
  dominates across all problem classes).
- **Cons:** harder to summarize; useful as supplementary material.

---

## 6. Aggregation recipes (composite math)

The composite is sensitive to scale choices. Recommended pipeline:

1. **Within a metric family:** for each metric, compute *per-package, per-k* values. Z-score
   within metric (across packages) so different scales align.
2. **Within a lens:** average z-scores (or use Borda count across the metric ranks). Bootstrap
   the average over particles to get a CI.
3. **Across lenses:** apply README weights → final composite score.
4. **Sanity check:** sensitivity analysis — perturb the README weights ±5%, see whether the
   package ranking flips. Report the rank in 100 perturbed runs as a probabilistic ranking.
5. **Report both** the composite *and* the per-pillar profile (Option B figure).

---

## 7. Concerns with the README §8 framework (raised, not enforced)

Per direction we do not edit README.md. The framework is preserved. The following concerns are
recorded here in case they later warrant revisiting:

### 7.1 Weight on FSC may be too low for the user-stated goal
README weights FSC resolution gain at 20%, but the user's clarification on 2026-06-02 ranks
"downstream STA resolution" highest. Suggest re-examining whether the 35/25/20/20 split mirrors
that priority. One alternative: 30 / 20 / 20 / 30 (FSC up to 30%, Stability down to 30%).
Probably worth running once and comparing rankings.

### 7.2 Internal validity in voxel space is unreliable
For 80³ subtomograms, the input dimension is ~512k. Euclidean distance becomes nearly uniform
above a few hundred dimensions (Beyer et al. 1999) — silhouette / DB / CH all degrade. README §4
already advises computing these in latent space; we should make that requirement *mandatory*, and
for packages without a latent space, use the N×k cross-correlation matrix as a low-d coordinate
(README §4 fallback). Document this strictly.

### 7.3 The four pillars are not orthogonal at low N
Bootstrap stability, internal validity, and cross-package agreement all measure facets of
"consistency"; at n=672 they're likely correlated. Effective dimensionality of the composite is
probably ≤3, not 4. Sensitivity analysis (§6.4) will catch this.

### 7.4 No metric in the README captures *discovery*
None of the four pillars rewards a method that surfaces a *biologically meaningful* but
previously unknown class. The closest proxy is "cross-package agreement on a robust subgroup that
is not in the soft GT." Worth flagging in the write-up.

### 7.5 Hubert-Arabie ARI inflation
ARI is mildly inflated when k is small and class sizes are imbalanced (Romano et al. 2016). At
k=2 and the real T4P phase imbalance (unknown), AMI is the safer scalar; report ARI as
companion only.

---

## 8. Concrete implementation notes (Python / current scripts)

- **Master matrix:** add a script `scripts/analysis/build_labels_matrix.py` that consumes each
  package's final assignment file (RELION `_data.star`, DISCA `class_labels.npy`, etc.) and
  produces `outputs/benchmark/labels_matrix.csv` indexed by master_particles.csv ID.
- **Lens A:** `sklearn.metrics` covers ARI, AMI, NMI, V-measure, homogeneity, completeness.
  Hungarian matching: `scipy.optimize.linear_sum_assignment` over the contingency table → then
  `sklearn.metrics.f1_score`.
- **Lens B:** half-set per class is the hard part. RELION's `relion_postprocess` can compute
  masked FSC given two half-maps. We already extract per-class resolution in
  `scripts/analysis/relion_class_report.py`; extend that to: (i) split each class's particles into
  half-sets, (ii) re-refine each half (or use random-half assignments if pose is already locked),
  (iii) compute masked FSC, (iv) integrate AUC. **Open question:** which packages let us specify
  half-sets? If most don't, fall back to pose-locked half-set FSC: take final aligned subtomograms,
  randomly split per class, average each half, compute FSC. Note this is *not* full
  gold-standard but is a tractable proxy.
- **Lens C:** Hennig clusterboot has no maintained Python equivalent we trust. Reimplement: for
  20 bootstrap draws of 80% of particles, rerun the package's classification, compute Jaccard of
  each original cluster to its best match in the resample, average across draws. For RELION/PyTom
  this means a few hundred CPU/GPU-hours — schedule with the team. (For DISCA, fast — full rerun
  is minutes.)
- **Lens D:** straightforward — pairwise `adjusted_rand_score` over the labels matrix; render as a
  heatmap. Co-occurrence: count `(labels_matrix[i] == labels_matrix[j]).sum(axis=package)` for
  each particle pair.

Existing analysis scripts that already do per-package summaries (and can be hubbed into the
master matrix): `scripts/analysis/relion_class_report.py`, `scripts/analysis/disca_report.py`,
`scripts/analysis/tomoflow_report.py`, `peet/PEET_classification_research.md`,
`dynamo/dynamo_outputs/`.

---

## 9. Recommended deliverables for the manuscript

1. **Master labels matrix CSV** (one row per particle, one col per package×k).
2. **Per-lens tables**: package × k → metric values.
3. **Pairwise ARI heatmap** (Lens D).
4. **Per-class FSC curves overlaid per package** (Lens B).
5. **Composite ranking** with bootstrap CI + weight-sensitivity table.
6. **Radar/profile figure per package** (Option B).
7. **Regime map** if synthetic sweeps permit (Option C).
8. **A "shared failure" section** documenting the 6-package miss-of-the-two-phases finding from
   STATUS.md — already the most publication-worthy result of the benchmark.

---

## 10. References

### Classical clustering evaluation
- Hubert, L. & Arabie, P. (1985). Comparing partitions. *Journal of Classification* 2, 193–218.
  (Adjusted Rand Index.)
- Vinh, N. X., Epps, J. & Bailey, J. (2010). Information theoretic measures for clusterings
  comparison: variants, properties, normalization and correction for chance. *JMLR* 11, 2837–2854.
  (AMI.) <https://jmlr.csail.mit.edu/papers/volume17/15-627/15-627.pdf>
- Romano, S., Vinh, N. X., Bailey, J. & Verspoor, K. (2016). Adjusting for chance clustering
  comparison measures. *JMLR* 17(1), 4635–4666.
- Rosenberg, A. & Hirschberg, J. (2007). V-measure: a conditional entropy-based external cluster
  evaluation measure. *EMNLP-CoNLL*.
- Rousseeuw, P. J. (1987). Silhouettes: a graphical aid to the interpretation and validation of
  cluster analysis. *Journal of Computational and Applied Mathematics* 20, 53–65.
- Davies, D. L. & Bouldin, D. W. (1979). A cluster separation measure. *IEEE TPAMI* 1(2), 224–227.
- Caliński, T. & Harabasz, J. (1974). A dendrite method for cluster analysis. *Communications
  in Statistics* 3, 1–27.
- Dunn, J. C. (1974). Well-separated clusters and optimal fuzzy partitions. *Journal of
  Cybernetics* 4, 95–104.
- Munkres, J. (1957). Algorithms for the assignment and transportation problems. *J. SIAM* 5,
  32–38. (Hungarian matching.)

### Clustering stability / consensus
- Hennig, C. (2007). Cluster-wise assessment of cluster stability. *Computational Statistics &
  Data Analysis* 52, 258–271. <https://www.homepages.ucl.ac.uk/~ucakche/papers/clusta.pdf>
- Monti, S., Tamayo, P., Mesirov, J. & Golub, T. (2003). Consensus clustering: A resampling-based
  method for class discovery and visualization of gene expression microarray data. *Machine
  Learning* 52, 91–118.
- Strehl, A. & Ghosh, J. (2002). Cluster ensembles — a knowledge reuse framework for combining
  multiple partitions. *JMLR* 3, 583–617.
- Fred, A. L. N. & Jain, A. K. (2005). Combining multiple clusterings using evidence
  accumulation. *IEEE TPAMI* 27(6), 835–850.
- Beyer, K. et al. (1999). When is "nearest neighbor" meaningful? *ICDT*. (Curse of dimensionality.)

### Cryo-EM resolution and validation
- Rosenthal, P. B. & Henderson, R. (2003). Optimal determination of particle orientation,
  absolute hand, and contrast loss in single-particle electron cryomicroscopy. *J. Mol. Biol.*
  333, 721–745. (FSC 0.143 gold standard, B-factor estimation.)
- Penczek, P. A. (2010). Resolution measures in molecular electron microscopy. *Methods in
  Enzymology* 482, 73–100.
- Kucukelbir, A., Sigworth, F. J. & Tagare, H. D. (2014). Quantifying the local resolution of
  cryo-EM density maps. *Nature Methods* 11, 63–65. (ResMap.)
- Tan, Y. Z., Baldwin, P. R., Davis, J. H., Williamson, J. R., Potter, C. S., Carragher, B. &
  Lyumkis, D. (2017). Addressing preferred specimen orientation in single-particle cryo-EM
  through tilting. *Nature Methods* 14, 793–796. (Sphericity / cFSC.)
- Lawson, C. L. et al. (2021). Cryo-EM model validation recommendations based on outcomes of the
  2019 EMDataResource challenge. *Nature Methods* 18, 156–164. (Map-to-model FSC.)

### Heterogeneity-specific benchmarks
- Jeon, M., Levy, A., Zhong, E., et al. (2024). CryoBench: Diverse and challenging datasets for
  the heterogeneity problem in cryo-EM. *NeurIPS 2024 Datasets & Benchmarks Track* (Spotlight).
  <https://arxiv.org/abs/2408.05526>, <https://cryobench.cs.princeton.edu/>. (Per-Conformation
  FSC, AUC-FSC, Sample FSC, Per-Image FSC, p_MN, Δ.)
- Zhong, E. D., Bepler, T., Berger, B. & Davis, J. H. (2021). CryoDRGN: reconstruction of
  heterogeneous cryo-EM structures using neural networks. *Nature Methods* 18, 176–185.
- Powell, B. M. & Davis, J. H. (2024). Learning structural heterogeneity from cryo-electron
  sub-tomograms with tomoDRGN. *Nature Methods* 21, 1525–1536.
  <https://www.nature.com/articles/s41592-024-02210-z>
- Punjani, A. & Fleet, D. J. (2021). 3D variability analysis: Resolving continuous flexibility
  and discrete heterogeneity from single-particle cryo-EM. *J. Struct. Biol.* 213, 107702.
- Glielmo, A. et al. (2022). Ranking the information content of distance measures. *PNAS Nexus*
  1(2). (Information Imbalance Δ.)

### Rank aggregation / multi-criteria benchmarking
- Borda, J. C. (1781). Mémoire sur les élections au scrutin. (Borda count.)
- Wolpert, D. H. & Macready, W. G. (1997). No free lunch theorems for optimization. *IEEE Trans.
  Evolutionary Computation* 1(1), 67–82.

### Information retrieval / general
- Manning, C. D., Raghavan, P. & Schütze, H. (2008). *Introduction to Information Retrieval*.
  Cambridge UP. (Purity, F-beta definitions.)
- Steinley, D. (2004). Properties of the Hubert-Arabie adjusted Rand index. *Psychological
  Methods* 9, 386–396.

> Honesty note: items in the "Information theoretic / Romano 2016 / Glielmo 2022" cluster are
> cited based on search-result references rather than full-paper reads. Authors and venues
> verified through cross-referenced searches; details (e.g., exact page ranges) may need a
> manual pass before going into a manuscript.

---

## 11. Open questions for the team

1. **Pillar weights:** are we comfortable with README 35/25/20/20 given Eben's stated priority on
   resolution? Or do we surface a 30/20/20/30 alternative as a secondary ranking?
2. **Soft GT framing:** is Dynamo's two-phase split sturdy enough to use as numerical reference,
   or should we report it only as a *qualitative* anchor and skip Lens A on real data?
3. **Synthetic sweep budget:** the regime map (Option C) needs ~3–5 dimensions of sweep. Is Josh's
   ETSimulations track scoped for that, or only the README's 2 base sets?
4. **Half-set FSC strategy:** pose-locked half-set FSC is tractable across all packages; true
   gold-standard refinement-from-scratch per class is not. Are we OK calling the proxy "half-set
   FSC" and being explicit about the distinction in the write-up?
5. **Discovery channel:** worth committing time to a "consensus minus soft-GT" analysis to surface
   any biological structure missed by all single-package runs but agreed-on by ≥3 packages?

