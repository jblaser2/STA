# emClarity — Install, GPU Validation, and Data-Fit Runbook

> Status: **installed + GPU-verified on this machine (RTX 5080 / sm_120)**, but **cannot be run on
> the real T4P subtomogram set** — emClarity is a tilt-series pipeline and has no path to ingest our
> 672 pre-extracted, tilt-series-free 80³ volumes. It belongs in the **synthetic-data** benchmark
> track (ETSimulations produces tilt series). Written 2026-06-01.

## 1. What emClarity is (and why our real data doesn't fit)

emClarity (Himes & Grigorieff, *eLife* 2021) is a **complete tilt-series → high-resolution STA
pipeline**, not a standalone classifier of pre-made subvolumes. Its workflow (tutorial Fig. 1):

```
autoAlign/ETomo → ctf estimate → define sub-regions → templateSearch (pick) → init
   → ctf 3d (reconstruct tomograms) → avg (subtomo average) → alignRaw (align)
   → [pca → cluster]  (classification, optional)  → final reconstruct
```

**Classification (`pca`, `cluster`) lives at the very end** and operates on subtomogram averages
built by `avg`, which re-extracts subvolumes from tomograms that **emClarity itself reconstructs**
(`ctf 3d`) from the aligned tilt series, applying a per-particle 3D-CTF / sampling function derived
from the tilt geometry.

**The import path is coordinates, not volumes.** Tutorial §8.5 ("Import particles from another
software") lets you supply your own `.csv` + `.mod` *particle-coordinate* files, but §9 (`init`)
still requires `fixedStacks/ctf/<prefix>_ali1_ctf.tlt` (the tilt-series CTF estimate) and you "should
still run `ctf estimate`" on the tilt series first. There is **no entry point that accepts a folder
of pre-extracted, pre-aligned `.mrc` subtomograms** the way Dynamo/PyTom/PEET/RELION-classic do.

⇒ Our real dataset (672 hand-picked, pre-aligned 80³ T4P subtomos, **no tilt series, no tomograms,
no IMOD alignment**) is **out of scope for emClarity**. This is the same wall as RELION 4/5's
pseudo-subtomo pipeline, but stricter — RELION 5 retained a classic 3D path; emClarity has none.

**Where emClarity *does* fit our project:** the planned **synthetic ETSimulations datasets** are
generated *from* tilt series (ETSimulations → tilt series → IMOD WBP). Those carry exactly the
tilt-series + geometry emClarity needs, so emClarity can be benchmarked there.

## 2. What's installed on this machine

| Asset | Path |
|---|---|
| emClarity 1.5.3.11 (compiled binary + run script) | `~/Applications/emClarity_install/emClarity_extracted/emClarity_1.5.3.11/` |
| `emClarity` launcher (symlink → `..._v19a` wrapper) | `~/.local/bin/emClarity` (on PATH) |
| MATLAB Compiler Runtime R2019a Update 9 (v96) | `~/Applications/MATLAB_Runtime/R2019a/v96/` |
| libcrypt.so.1 shim (RHEL10 fix, see §4) | `~/Applications/emClarity_install/extralib/` |
| GPU smoke test (cuFFT + rescale) | `~/Applications/emClarity_install/gputest/` |
| Tutorial PDF (v1.5.3.10) | `~/Downloads/emClarity-tutorial-V1-5-3-10.pdf` |

Dependencies satisfied: IMOD 5.1.12 (≥4.10.18 ✓), CUDA 13.2 driver 595.71.05.

### Install recipe (for reproducing on a fresh machine)
1. **emClarity binary** — download `emClarity_1.5.3.11.tar.gz` (actually a zip, 266 MB) from the
   wiki Google-Drive link (`gdown 1CsyVCUsSki14vLV954OjKfwmyB3YLJEE`), `unzip` it.
2. **MCR R2019a Update 9** — `MATLAB_Runtime_R2019a_Update_9_glnxa64.zip` (2 GB) from mathworks SSD;
   `./install -mode silent -agreeToLicense yes -destinationFolder ~/Applications/MATLAB_Runtime/R2019a`.
3. **Edit the run script** `bin/emClarity_1_5_3_11_v19a`:
   - `MCR_BASH=` → `<MCR>/v96/{runtime,bin,sys/os,extern/bin}/glnxa64` (colon-joined).
   - `export emClarity_ROOT=` → the extracted `emClarity_1.5.3.11` dir.
   - prepend the libcrypt shim dir to the `LD_LIBRARY_PATH=` line (§4).
4. Symlink `~/.local/bin/emClarity` → that wrapper.

## 3. The GPU question — RESOLVED: it works on Blackwell (sm_120)

emClarity 1.5.3.11 ships **CUDA-10-era** GPU code: bundled `libcufft.so.10.1.1.243`,
`libcublas.so.10.2.1.243`, and MATLAB-R2019a-compiled gpuArray kernels (CUDA 10.0 runtime,
`libcudart.so.10.0` inside the MCR). The RTX 5080 is **sm_120 (Blackwell)** — three generations
newer than the newest natively-supported arch (Ampere sm_80, and only in emClarity 1.6.1). Prediction
was that the precompiled kernels would fail with "no kernel image available".

**Empirically they do NOT fail.** The **CUDA 13.2 driver (595.71.05) forward-JIT-compiles the old
embedded PTX to sm_120 at runtime**, for both:
- bundled cuFFT 10.1 — direct 80³ C2C FFT test returned the correct DC term
  (`gputest/test_cufft.c`, DC = 1,535,997 ≈ 512000 × mean3);
- MATLAB CUDA-10 gpuArray kernels — `emClarity rescale in.mrc out_gpu.mrc 13.328 10.0 GPU`
  produced a valid 107³ volume (no NaNs, sane density).

⇒ **No source build, no 1.6.1, no legacy CUDA toolkit needed.** The shipped 1.5.3.11 binary runs on
this GPU as-is. (If a future driver ever drops old-PTX JIT, 1.6.1 — Ampere-native, CUDA 11 — is the
fallback.)

### Validated GPU smoke test
```bash
emClarity rescale in.mrc out_gpu.mrc 13.328 10.0 GPU   # FFT-based resample on the GPU
```
Usage (from `testScripts/emClarity.m`): `emClarity rescale fileIn fileOut angPixIN angPixOUT cpu/GPU`.

## 4. Gotcha: libcrypt.so.1 on RHEL 10

The compiled binary needs `libcrypt.so.1`, dropped from glibc on RHEL 9/10 (moved to the
`libxcrypt-compat` package). Without root we shimmed a real libxcrypt `.so.1` found on the box:
```bash
mkdir -p ~/Applications/emClarity_install/extralib
cp /opt/saltstack/salt/lib/libcrypt.so.1.1.0 ~/Applications/emClarity_install/extralib/
ln -sf libcrypt.so.1.1.0 ~/Applications/emClarity_install/extralib/libcrypt.so.1
# then prepend that dir to LD_LIBRARY_PATH inside the wrapper
```
(Do **not** symlink `libcrypt.so.1 → libcrypt.so.2`; the `.2` soname is ABI-different.)
If you have root, `sudo dnf install libxcrypt-compat` is the clean fix.

## 5. Sanity commands
```bash
emClarity help     # lists all sub-commands
emClarity check    # verifies install paths (note: does NOT exercise the GPU; first run ~3 min JIT)
```

## 6. Next steps (when synthetic data exists)
Run the full pipeline on an ETSimulations synthetic set that has tilt series:
`autoAlign → ctf estimate → templateSearch → init → ctf 3d → avg → alignRaw → pca → cluster`.
Classification algorithm details: tutorial §14 + §16.11 (combine half-maps, resolution bands,
difference maps, SVD, clustering). That is the emClarity contribution to the k=2/3/4 benchmark on
synthetic ground truth.
