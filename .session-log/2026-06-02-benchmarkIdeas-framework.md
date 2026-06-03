# 2026-06-02: Benchmark Framework Research and Design

## Goal
Design a comprehensive evaluation framework for the STA classification benchmark that addresses three
open concerns: (1) F-beta vs ground truth does not directly measure downstream STA resolution, (2) does
not characterize when different algorithms win (regime-specific performance), (3) not extensible to
datasets without ground truth.

## What Happened
Conducted extensive literature review on cryo-EM/cryo-ET classification benchmarking via parallel web
searches and fetches. Reviewed:
- CryoBench (Jeon et al. 2024 NeurIPS Spotlight) — metrics, datasets, heterogeneity benchmarking
- tomoDRGN (Powell et al. 2024 Nature Methods) — cryo-ET heterogeneity evaluation
- Clustering evaluation: Hennig 2007 bootstrap clusterboot, Monti 2003 consensus clustering, ARI/AMI/NMI
  (Hubert & Arabie 1985, Vinh et al. 2010, Rosenberg & Hirschberg 2007)
- Internal validity: Silhouette, Davies-Bouldin, Calinski-Harabasz, Dunn indices
- FSC standards and per-class resolution metrics (Rosenthal & Henderson 2003, Lawson et al. 2021)
- Rank aggregation: Borda count, Kemeny ranking (Lin 2010, Hadjar 2024)
- Cross-package consensus matrices and pairwise ARI (Strehl & Ghosh 2002)
- No-free-lunch theorem implications for regime-conditioned benchmarking

Synthesized research into comprehensive design document (`benchmarkIdeas.md`):
- Four-lens framework: (A) external validity vs GT, (B) downstream STA resolution, (C) stability/robustness,
  (D) cross-method consensus
- Vetted metric catalog (25+ citations) for each lens
- Real-data track (T4P with Dynamo soft-GT) and synthetic-data track design
- Four output format options with recommendation: multi-pillar profile + composite score
- Implementation notes tied to existing analysis scripts
- Explicit addressing of user's three concerns via metric choices and GT-free extensions
- Five concerns about the existing README §8 framework (not edited; raised in benchmarkIdeas.md §7)
- Five open questions back to team for resolution before execution

## Files Changed
- **Created:** `STA/benchmarkIdeas.md` (~370 lines; single canonical source for benchmark evaluation framework)
- **Updated:** `STA/STATUS.md` — "Last updated" line, "Now/Next/Parked" refreshed, "Open Decisions" extended
  with 5 new items tied to benchmarkIdeas.md §11

## Where I Stopped
Completed literature research, synthesis, writing, and git-staging. Document ready for team review.

## Next Step
(1) Eben and Josh review `benchmarkIdeas.md` and answer the five open questions in §11. (2) Once team
consensus on the framework, execute Lens A/B/C/D metrics on the existing 9-package real-data runs.
(3) For synthetic data: confirm with Josh what synthetic sweep scope is feasible, then populate the regime
map (Option C output format).
