# Executive Summary  
This report provides a comprehensive overview of RELION’s subtomogram 3D classification workflow (Class3D) and how to apply it to a pilus dataset. We first describe the Bayesian maximum-likelihood algorithm RELION uses for multi-reference 3D classification of subtomograms, including its mathematical formulation, use of pseudo‐subtomograms, priors, and handling of missing-wedge and CTF effects【20†L372-L380】【28†L10-L15】. Next we give a step-by-step protocol for running RELION Class3D on pre-aligned pilus subtomograms, including required inputs, parameter choices (box size, classes, sampling, regularization *T*, masks, symmetry), and example command lines. We estimate resources (CPU/GPU and time) for a few-hundred-particle dataset and explain how to interpret outputs. Common issues (overfitting, class collapse, alignment errors, missing-wedge artifacts) and diagnostics (log-likelihood, class occupancy, FSC curves, slice-views) are discussed, along with mitigation strategies (e.g. limiting resolution in the E-step to prevent overfitting【24†L128-L133】). We also provide pre- and post-processing checklists and tables summarizing parameter effects. Throughout, we cite RELION documentation and source-code references, as well as key literature on RELION subtomogram averaging, to ground recommendations in authoritative sources.

```mermaid
flowchart LR
    Start([Begin STA Workflow]) --> Prep[Preprocess tomograms<br/> & pick particles]
    Prep --> Extract{Extract pseudo‑subtomograms}
    Extract --> Cls3D[Run 3D Classification (relion_refine)]
    Cls3D --> Select[Select good classes<br/> & particles]
    Select --> Refine[High‑resolution 3D Refinement]
    Refine --> Finish([Results: final maps, FSC, classes])
```

## Algorithmic Framework of RELION Subtomogram Classification  
RELION performs subtomogram classification by maximising a Bayesian posterior probability of the 3D class maps given the data.  The underlying objective (negative log-posterior) is the sum of a data likelihood term and a Gaussian regularisation prior on the map’s Fourier coefficients【20†L372-L380】.  Using Bayes’ theorem, the target function can be written as 
$\displaystyle \text{(Regularised likelihood)} \;=\; -\ln P(\text{data}|\text{model}) - \ln P(\text{model})$【20†L287-L296】, 
where the likelihood assumes independent Gaussian noise in all Fourier pixels【20†L300-L308】.  In single-particle cryo-EM, the log-likelihood for one particle image (given a hypothetical orientation and translation) is the noise-weighted sum of squared differences between the experimental image and the projected model【20†L303-L312】.  In tomography, this is extended by summing over all tilted images of a particle: effectively the log-likelihood of observing that particle in each tilt image orientation【20†L319-L327】.  

To avoid explicitly summing over millions of 2D tilt images at each refinement step, RELION-4.0 introduces *pseudo-subtomograms*.  Each pseudo-subtomogram is a 3D volume whose Fourier voxels accumulate contributions from the tilt images:  
- A *data* array that contains the sum of all CTF-weighted tilted images mapped into 3D Fourier space.  
- A *weight* array holding the sum of the squared CTFs for those images at each voxel.  
- A *multiplicity* array (concatenated in the weight output) that counts how many tilt projections contribute to each voxel【28†L10-L15】【20†L342-L350】.  
Mathematically, summing Eq.4 (likelihood over tilt images) is approximated by summing over the pseudo-subtomogram voxels (Eq.7)【20†L342-L350】.  In this way, RELION reuses its single-particle optimization code: each pseudo-subtomogram effectively encodes the 2D data of the entire tilt-series for that particle【28†L10-L15】【20†L342-L350】.  (All CTF and tilt geometry are applied in constructing the pseudo-volumes.)

The classification itself proceeds by an Expectation–Maximization (EM) algorithm akin to standard RELION 3D classification.  In the E-step, each particle is probabilistically assigned to classes based on the likelihood of observing its pseudo-data given each class map and orientation.  In the M-step, the class 3D maps are updated by summing all contributions from particles, weighted by these probabilities, while applying an “$L_2$” regularisation (Tikhonov) prior【20†L372-L380】.  Concretely, the maps $\{ M_k \}$ and noise variance estimates are iteratively refined using formulas (see Equations 11–13 in【20†L372-L380】) which combine the accumulated data term, weights, and an estimate of the signal power spectrum.  This yields a set of $K$ class volumes.  Each class 3D map is therefore the maximum *a posteriori* reconstruction given its subset of particles.

RELION further uses Gaussian priors on particle orientations and positions to incorporate experimental knowledge and prevent overfitting【20†L398-L400】.  For example, one can restrict out-of-plane tilt (“rocking”) by specifying a small prior width on the tilt angle (e.g. if filaments lie in a membrane plane).  These priors effectively limit the search range in the E-step and enforce local orientational coherence【20†L398-L400】.  In practice, Class3D usually involves two nested searches: a coarse global alignment search and then finer local searches, though these can be disabled to speed up classification at the risk of missing correct alignments.

Because RELION’s STA pipeline uses pseudo-subtomograms, *no explicit missing-wedge correction* is applied during classification.  By formulating the likelihood as if optimizing against the original 2D tilt images, the data model inherently accounts for the limited angular coverage【15†L680-L688】.  In other words, pseudo-subtomograms allow the likelihood comparison to naturally ignore unsampled Fourier regions, eliminating the need for separate “missing-wedge” filters.  The remaining artifacts of anisotropic sampling are thus handled statistically through the noise-weighting, rather than by an ad hoc mask【15†L680-L688】.

<p style="margin-top:0.5em">
**Key points:** RELION’s subtomogram Class3D is essentially a GPU-accelerated, multi-class 3D refinement using expectation-maximization.  It works with pseudo-subtomograms that encode all tilt images of each particle【28†L10-L15】.  The algorithm maximizes a regularised (MAP) likelihood; map updates follow EM formulas【20†L372-L380】.  Priors (on rotations/translations) and a Tikhonov regularizer (parameter *T*) control noise suppression【20†L398-L400】【24†L93-L100】.  Missing-wedge effects are implicitly handled via the pseudo-subtomogram model【15†L680-L688】.  Because classification often involves alignment, GPU acceleration is normally used; classification without alignment (just separating classes) can run on CPU【4†L49-L53】.  
</p>

## Step-by-Step Protocol for Class3D on Pilus Data  

**1. Prepare inputs.** Ensure you have: (a) a STAR file of subtomogram particle locations and (optionally) known orientations (the *Particle star*); (b) a *Tomogram star* containing tilt-series alignment and CTF info for each tomogram; and (c) (if done) a *Trajectory star* file with motion parameters. These typically come from earlier tomogram alignment and particle picking jobs. All particles should be roughly centered and binned appropriately.  

**2. Extract pseudo-subtomograms.** Run `relion_tomo_subtomo` to build pseudo-volumes. For example:  
```
relion_tomo_subtomo --i particles.star --tomo tomograms.star --ctf tomograms.star \
    --b 128 --crop 96 --bin 4 --o PseudoSubtomo/job001
```  
Here `--b` is the initial (oversized) box in pixels (set ~1.5× the longest particle dimension【4†L79-L84】), `--crop` is the final box to keep (e.g. downsampled), and `--bin` is the binning factor.  Downsampling (e.g. bin=4) is common initially to speed up.  The job outputs a new particle STAR and MRC stacks of each pseudo-subtomogram (data, weights, multiplicity)【28†L10-L15】.  These become the inputs to `relion_refine` (Class3D).  

**3. Choose an initial reference.** If no reference is given, RELION can perform “**3D initial model**” first.  Otherwise, provide a low-resolution reference map (e.g. a Gaussian blob or previous average). Always low-pass filter this to a low cutoff (e.g. 60–80Å) to avoid bias【24†L93-L100】.  Ensure `--ini_high` (initial low-pass) is set accordingly (e.g. `--ini_high 60`).  

**4. Design mask.** Make a 3D mask that encloses the pilus shape (e.g. a cylinder or ellipsoid covering the filament). The mask should roughly match particle size (diameter of pilus, plus a few nm) and taper to zero at edges. In many cases, a simple soft-edged sphere or cylinder with diameter ~1.2–1.5× the pilus width is fine. Specify this mask in `--mask`.  If no mask is given, RELION uses a default sphere based on the particle diameter parameter.  

**5. Set Class3D parameters.** On the command line or GUI, configure:  
- **Number of classes (K):** Start with a small K (e.g. 2–4). For a few-hundred particles, 2–5 classes is typical (too many classes wastes computation and yields few particles per class). The CPU/GPU time and memory scale roughly linearly with K【24†L89-L92】.  
- **Regularization (tau2_fudge, often called *T*):** Choose T≈2–4. RELION’s default for 3D is 2–4【24†L93-L100】. Higher *T* yields smoother (lower-resolution) class averages, while lower *T* can sharpen features but risks overfitting. For example, set `--tau2_fudge 3`.  
- **Angular sampling:** For initial runs, use coarse steps (e.g. 5° or 7°). After a few iterations, refine with finer sampling (e.g. 2–3°). Use `--angpix`/`--sigma_rot` or corresponding GUI fields. In the GUI “Sampling” tab, set *Initial Sampl. Interval* large and enable *Local search* with finer step.  
- **Mask particle during alignment:** Enable “Mask particles with zeros” (if using GUI) so alignment ignores outside noise. This matches removing background density.  
- **Limit resolution in E-step:** To avoid overfitting, you may set `--limit_resolution_e-step` (e.g. 15Å) so that only low frequencies are used in the alignment phase【24†L128-L133】. This prevents the alignment from chasing high-frequency noise.  
- **Symmetry:** If the pilus has known helical symmetry (repeat distance and rotation), use Relion’s **Helical reconstruction** mode by specifying the twist and rise; otherwise set `--sym C1`. If the filament symmetry is unknown, run classification in C1 to let RELION find it.  

**6. Run 3D Classification (relion_refine).** Invoke RELION on the pseudo-subtomogram STAR with the chosen settings. Example command:  
```bash
relion_refine --o Class3D/job002 \
    --i PseudoSubtomo/job001/particles.star \
    --ref initial_reference.mrc --ini_high 60 \
    --K 3 --sym C1 --mask pilus_mask.mrc \
    --angpix 3.5 --tau2_fudge 3 --particle_diameter 150 \
    --dont_combine_weights_via_disc --j 8 --gpu "0"
```  
This runs 3 classes (`--K 3`) with C1 symmetry, 3×3.5Å pixel size, and diameter ~150Å, using 8 CPUs and GPU 0. Adjust parameters to your data (box size, pixel, etc). The `--dont_combine_weights_via_disc`/`--gpu` flags control parallelism (multi-threading/GPU use).  Monitor the log for the progress of iterations.

**7. Expected Runtime.** Classification is compute-intensive. For **hundreds of particles** at moderate box-size (~96–128 px) and 3–5 classes, each iteration may take minutes on a GPU; a full 25–50 iteration run could take a few hours on a modern GPU (e.g. NVIDIA A100/RTX)【4†L49-L53】. On CPU-only machines, expect significantly longer (often impractical for large 3D searches). The exact time depends on angular sampling, number of classes, and box size. A rough estimate: ~1–2 hours on 1 GPU for 200–1000 particles with 3 classes and ~5° angular steps (as seen in SPA examples【39†L129-L132】). 

**8. Analyze outputs.** After the run, RELION writes:  
- `run_itXXX_class00Y.mrc` – the 3D volume of class Y from the last iteration (for Y = 1..K).  
- `run_itXXX_optimiser.star` – contains particle-to-class assignments and per-iteration scores (likelihood, sigma², etc).  
- `run_itXXX_model.star` – the (Bayesian) reconstruction model and noise spectrum for each class.  
- Logfile and other STAR files.  

Use the Relion GUI or scripts to inspect classes. View slices through each class volume: poor classes (e.g. junk) often look blurry or empty in slices【24†L149-L158】. Plot the class occupancy (star field `rlnClassDistribution` in `optimiser.star`). A well-behaved classification will have nonzero fractions for good classes and maybe some small junk classes. You can use `relion_plot_class_occupancy.py` or similar to visualize.  The individual 3D maps can be opened in Chimera/ChimeraX.  

```mermaid
flowchart TD
    ClassRun([Class3D Job Outputs])
    Maps>Volumes:run_it###_class001.mrc ... classN]
    Star[run_it###_optimiser.star (class assignments)]
    ClassRun --> Maps
    ClassRun --> Star
    Star --> Plot[Plot class distributions]
    Maps --> View3D[View slices in Chimera]
    Plot -.-> Diagnose[Check for uneven or empty classes]
    View3D -.-> Diagnose
```

## Troubleshooting and Diagnostics  

- **Class collapse / duplication:**  If two or more classes converge to nearly identical maps, it may indicate too many classes or too low regularization *T*. Reduce *K* or increase `--tau2_fudge`. Conversely, if classes all look too noisy, try lowering *T*. In all cases, inspect the FSC (gold-standard) curves if available to see if high-frequency content is reliable.  

- **Overfitting:** Watch the log’s per-iteration likelihood and resolution metrics. If class volumes show high-resolution noise (“grainy” features) and the E-step limit (see `run_it###_data.star`) is exceeded, consider limiting the alignment resolution (e.g. to 10–15Å)【24†L128-L133】. You can also increase *T* to suppress high-frequency variability【24†L93-L100】. Relion’s “half-map” approach (if enabled) will reveal overfitting as an early rise in FSC.  

- **Alignment errors:**  Poor or inconsistent orientations can lead to smeared averages. If subtomogram orientations were pre-determined (e.g. by template matching), check that you enabled “Use prior orientations” (`--initial_ang`) so RELION respects them.  If classification was done without aligning (set *Perform image alignment?*: No), the results will only separate pre-aligned classes and may be faster on CPU. If alignments seem incorrect, run a small test with coarse angular sampling (e.g. 7°) to ensure global alignment works, then refine locally.  

- **Missing-wedge artifacts:** While pseudo-subtomograms mathematically handle the missing wedge, in practice you may see stripes or elongation artifacts in class averages. This can happen if tilt geometry information (CTFs, alignments) is inaccurate. Verify that the Tomogram STAR inputs are correct. Re-running `relion_tomo_subtomo` after any change in tilt alignment or CTF is important, as pseudo-volumes must reflect the latest geometry【28†L10-L15】.  

- **Monitoring metrics:**  Key values to track in the log or `optimiser.star` are the total (negative) log-likelihood, *rlnMaxValueProbDistribution* (sum of particle probabilities), and *sigma²* terms. Steady increase in log-likelihood and stable noise estimates indicate convergence. The GUI “Display 3D classes” tool can sort classes by occupancy (use `rlnClassDistribution`) so you quickly see which classes captured most particles【39†L161-L169】.  

- **Validation:** After classification, it is common to run a 3D auto-refinement on the best class (or a subset of classes) to get a higher-resolution reconstruction. Check the gold-standard FSC between half-maps of refined classes. Also, validate that the class separations make sense (e.g. distinct structural states of the pilus). 

## Checklist of Preparatory Steps and Validation  
Before running Class3D, ensure:  
- [ ] **Pre-alignment completed:** Tomograms aligned and CTFs estimated; trajectories (particle motion) refined if applicable. Import or update tomogram STAR files in RELION.【32†L11-L19】  
- [ ] **Particle picking verified:** Subtomogram coordinates are correct; remove duplicates or outliers. Subtomos should be centered on the pilus.  
- [ ] **Pseudo-subtomograms re-generated:** If any CTF or alignment changed, re-run `relion_tomo_subtomo` to update the pseudo-volumes【28†L10-L15】.  
- [ ] **Mask tested:** Create a provisional mask (e.g. spherical or cylindrical) to confirm it encloses the particle without truncation. Visualize it on the initial average.  
- [ ] **Initial average checked:** Build a quick initial average (e.g. by running *Reconstruct particle* on the pseudo-stacks) to see if signal is present. 

After classification, do:  
- [ ] **Inspect class volumes:** Visualize slices and isosurfaces to identify distinct classes or junk. Check that good classes show expected pilus density.  
- [ ] **Check class occupancy:** Ensure at least one class contains a significant fraction of particles (otherwise, too many classes were used). Plot occupancy vs. class index.  
- [ ] **Compute FSC/resolution:** If you split particles by class and refine, check FSC curves and local resolution.  
- [ ] **Subset selection:** Use the *Subset selection* job (or `relion_star_subset`) on the final `run_it###_optimiser.star` to extract stars for chosen classes, then proceed to refine.  

## Recommended Parameters for Pilus Subtomograms  

| Parameter                     | Suggested Setting (pilus data)                 | Notes/Effect (Scaled per data volume)  |
|-------------------------------|-----------------------------------------------|----------------------------------------|
| **Box size (px)**             | ~96–128 px (covering ~1.5× pilus diameter)    | Choose so that the filament is centered with margin【4†L79-L84】. Bigger box→ better accommodating filaments but slower. |
| **Mask diameter (Å)**         | ≈75–150 Å (pilus width + buffer)              | Mask encloses filament; use cylindrical or spherical mask. “Mask particles with zeros” in RELION to ignore background. |
| **Number of classes (K)**     | 2–5                                           | Small K focuses on major states. Cost ∝ K【24†L89-L92】. Too many classes dilutes particles. |
| **Regularization (tau2_fudge)**| 3 (≈T=3)                                     | Typical 3D classification uses T=2–4【24†L93-L100】. Raise to smooth classes; lower to sharpen. |
| **Initial filter (Å)**        | 50–60 Å                                       | Low-pass filter on input reference. Prevents bias from high-res noise. |
| **Angular sampling**          | 5–7° (initial), refine to 2°                  | Coarse for early iterations, then finer. Local searches enabled. |
| **Tilt-angle prior**          | ~10–20° (optional)                            | If pili lie on a membrane plane, restrict out-of-plane tilt. Use `--sigma_tilt`. |
| **Symmetry**                  | C1 (or helical if known)                      | RELION can impose known helical sym (twist/rise). If unsure, use C1 and verify symmetry after. |
| **GPU usage**                 | Yes (for aligned classification)              | RELION Class3D will utilize GPUs by default. For classification *without* orientation searches, CPU-only is possible but slower【4†L49-L53】. |
| **E-step resolution limit**    | 10–15 Å (optional)                            | Limits alignment to low-frequencies to avoid overfitting【24†L128-L133】. Useful if data is noisy. |

## Sample Command-Line Examples  

```bash
# 1) Extract pseudo-subtomograms (bin 4, box 128 -> crop 96):
relion_tomo_subtomo --i particles.star --tomo tomograms.star --ctf tomograms.star \
    --b 128 --crop 96 --bin 4 --o PseudoSubtomo/job001

# 2) Run 3D classification on pseudo-subtomograms:
relion_refine --o Class3D/job002 \
    --i PseudoSubtomo/job001/particles.star \
    --ref initial_model.mrc --ini_high 60 \
    --K 3 --sym C1 --mask pilus_mask.mrc \
    --angpix 3.5 --tau2_fudge 3 --particle_diameter 150 \
    --dont_combine_weights_via_disc --j 4 --gpu "0"
```

In the above, replace `--particle_diameter 150` and `--angpix 3.5` with your actual pixel size and pilus diameter. Add `--helical` options if imposing helical symmetry. The `--gpu "0"` argument uses GPU 0; omit or set `--gpu ""` to run on CPU only (useful for no-alignment runs). 

## Common Pitfalls and Tips  

- **Overfitting to noise:** If class averages are speckled or show features below expected resolution, raise the regularisation (`--tau2_fudge`) or limit the high-resolution alignment (`--limit_resolution_e-step`)【24†L128-L133】. Monitor the log for extremely high likelihood values which can signal overfitting.  
- **Class collapse / duplicates:** Classes should represent distinct density; if multiple classes look identical or empty, you likely used too many classes. Reduce *K* or increase *T*. Check that no particles are duplicated in the input STAR.  
- **Alignment instabilities:** With very noisy data, RELION might misalign particles between classes. If “Perform image alignment” is off (no re-alignment), classification will run faster (on CPU) but cannot correct mis-picks. If using alignment, ensure enough angular samples and consider an external initial alignment (e.g. template match angles) to seed RELION.  
- **Missing-wedge streaks:** Although pseudo-subtomos account for missing data, poor tilt-series alignments can still cause artifacts. Always verify CTF and tilt alignment quality. Use post-reconstruction local resolution and slices (e.g. Inspect with Chimera’s “voltex” and slice views) to spot wedge-induced blurring.  
- **Convergence checks:** The log file shows `rlnLogLikeliContribution`. It should plateau. Also check that the free (gold-standard) FSC of each class (if using half-split) makes sense.  
- **Automated class selection:** Use Relion’s *Display Classes* tool to sort by occupancy (rlnClassDistribution) and quickly identify classes with few particles (likely junk)【39†L161-L169】. These can be excluded.  

## Checklist Before and After Classification  

**Before Class3D:**  
- Tomogram alignment and CTF estimation complete (checked via e.g. cross-correlation curves).  
- Subtomograms extracted and centered correctly (run *Reconstruct particle* to verify average)【32†L21-L29】.  
- Pseudo-subtomograms generated *after* final CTF/tilt refinement (if any parameters changed, redo them)【28†L10-L15】.  
- Duplicate or badly aligned particles removed from STAR (use particle-cleanup tools).  
- Appropriate initial model or reference prepared and low-pass filtered.  

**After Class3D:**  
- Examine each class map for meaningful structure (use slice view in Chimera).  
- Plot class occupancies; classes with very low occupancy (< a few %) are likely junk.  
- (Optional) Use *Subset selection* to extract stars for the best class(es) and do a high-resolution refine.  
- Compute FSC on selected class particles. Ensure resolution is plausible and not driven by noise.  
- Cross-check that class separation agrees with any prior knowledge (e.g. pilus length or composition variants).  

Throughout, make use of RELION’s logs and GUI plotting tools. In particular, inspect the optimiser STAR file (`run_it###_optimiser.star`) for `rlnMaxValueProbDistribution` (sum of probabilities) and `rlnGroupNumber` (class IDs) to diagnose behavior.  Keep track of RELION messages (`.txt`) for warnings about particles running out of mask or any geometry issues. 

**References:** The RELION Subtomogram Averaging documentation and source code underpin this workflow.  Key algorithmic details come from the RELION-4.0 tomography methods paper【20†L372-L380】【15†L680-L688】 and the RELION program guide【28†L10-L15】. Practical parameter advice is drawn from the RELION tutorials【24†L93-L100】【4†L79-L84】 and community resources. The cited lines above point to official RELION manuals and publications for verification.
