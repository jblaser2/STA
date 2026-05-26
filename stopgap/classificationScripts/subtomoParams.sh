#!/usr/bin/env bash
## subtomoParams.sh
# Generates subtomo_param.star for a full 9-iteration alignment schedule.
# Run this ONCE before job submission — the parser appends three task blocks
# (iterations 1–3, 4–6, 7–9) to the same param file in sequence.
#
# Because all particles are z-axis aligned, cone search is used throughout
# rather than a full sphere search. In-plane phi is searched over ±180° at
# each stage to cover all in-plane rotations.

set -e
set -o nounset

export STOPGAPHOME=/home/ejl62/summerResearch/STOPGAP/exec
parser="${STOPGAPHOME}/bin/stopgap_parser.sh"

# ---- PATHS -----------------------------------------------------------------
param_name='params/subtomo_param.star'
rootdir='/home/ejl62/nobackup/autodelete/stopgapClassification/subtomo_project/'

motl_name='motl'
ref_name='ref_class1'
mask_name='ali_mask.mrc'
ccmask_name='ccmask.mrc'
wedgelist_name='wedgelist.star'
subtomo_name='subtomo'

# Filters — set calc_ctf=1 and calc_exp=1 if wedgelist has defocus/exposure
calc_ctf=0
calc_exp=0
cos_weight=0
score_weight=0.01

# Fixed settings (unchanged across all blocks)
binning=1
search_mode='hc'
search_type='cone'
cone_search_type='complete'
apply_laplacian=0
scoring_fcn='flcf'
symmetry='C1'
score_thresh=0
subset=100
avg_mode='full'
ignore_halfsets=0
temperature=0
rot_mode='linear'
fthresh=800
hp_rad=1
hp_sigma=2

# In-plane phi search: ±180° at each stage (full 360° coverage).
# phi_angincr × phi_angiter = 180 → e.g. 10° × 18 steps
phi_angincr=10
phi_angiter=18

# Unused Euler-axis options (cone search uses angincr/angiter instead)
euler_axes='zxy'
euler_1_incr=1; euler_1_iter=1
euler_2_incr=1; euler_2_iter=3
euler_3_incr=1; euler_3_iter=1

# Spectral / external filter options (all disabled)
specdir='none'; ps_name='none'; amp_name='none'; specmask_name='none'
ali_reffilter_name='none'; ali_particlefilter_name='none'
avg_reffilter_name='none'; avg_particlefilter_name='none'
reffiltertype='none'; particlefiltertype='none'
subtomo_mode='ali_singleref'

# Directory layout (use STOPGAP defaults)
tempdir='none'; commdir='none'; rawdir='none'; refdir='none'
maskdir='none'; listdir='none'; fscdir='none'; subtomodir='none'; metadir='none'

# ---- PARAMETER RANGES (reference) -----------------------------------------
# BLOCK      startidx  iterations  angincr  angiter  lp_rad  Purpose
# Block 1       1          3         10°       2      13      Coarse bootstrap
# Block 2       4          3          5°       3      17      Mid refinement
# Block 3       7          3          3°       3      22      Fine convergence
#
# angincr × angiter = half-cone angle (degrees from z-axis).
# lp_rad interpretation for box_size=80, pixel_size=13.33 Å:
#   lp_rad=13  → ~82 Å resolution
#   lp_rad=17  → ~63 Å resolution
#   lp_rad=22  → ~48 Å resolution
#   lp_rad=40  → ~27 Å resolution (Nyquist for 80-voxel box)
# Tighten lp_rad as resolution improves and angular search converges.
# ---------------------------------------------------------------------------

run_block() {
    local startidx=$1
    local iterations=$2
    local angincr=$3
    local angiter=$4
    local lp_rad=$5
    local lp_sigma=3

    echo "Appending block: startidx=${startidx}, iterations=${iterations}, angincr=${angincr}, angiter=${angiter}, lp_rad=${lp_rad}"

    eval "${parser} subtomo \
      param_name ${param_name} rootdir ${rootdir} \
      tempdir ${tempdir} commdir ${commdir} rawdir ${rawdir} \
      refdir ${refdir} maskdir ${maskdir} listdir ${listdir} \
      fscdir ${fscdir} subtomodir ${subtomodir} metadir ${metadir} \
      subtomo_mode ${subtomo_mode} startidx ${startidx} iterations ${iterations} \
      motl_name ${motl_name} wedgelist_name ${wedgelist_name} binning ${binning} \
      ref_name ${ref_name} subtomo_name ${subtomo_name} \
      mask_name ${mask_name} ccmask_name ${ccmask_name} \
      ali_reffilter_name ${ali_reffilter_name} ali_particlefilter_name ${ali_particlefilter_name} \
      avg_reffilter_name ${avg_reffilter_name} avg_particlefilter_name ${avg_particlefilter_name} \
      reffiltertype ${reffiltertype} particlefiltertype ${particlefiltertype} \
      specdir ${specdir} ps_name ${ps_name} amp_name ${amp_name} specmask_name ${specmask_name} \
      search_mode ${search_mode} search_type ${search_type} \
      euler_axes ${euler_axes} \
      euler_1_incr ${euler_1_incr} euler_1_iter ${euler_1_iter} \
      euler_2_incr ${euler_2_incr} euler_2_iter ${euler_2_iter} \
      euler_3_incr ${euler_3_incr} euler_3_iter ${euler_3_iter} \
      angincr ${angincr} angiter ${angiter} \
      phi_angincr ${phi_angincr} phi_angiter ${phi_angiter} \
      cone_search_type ${cone_search_type} \
      apply_laplacian ${apply_laplacian} scoring_fcn ${scoring_fcn} \
      lp_rad ${lp_rad} lp_sigma ${lp_sigma} hp_rad ${hp_rad} hp_sigma ${hp_sigma} \
      calc_exp ${calc_exp} calc_ctf ${calc_ctf} \
      cos_weight ${cos_weight} score_weight ${score_weight} \
      symmetry ${symmetry} score_thresh ${score_thresh} subset ${subset} \
      avg_mode ${avg_mode} ignore_halfsets ${ignore_halfsets} \
      temperature ${temperature} rot_mode ${rot_mode} fthresh ${fthresh}"
}

# Append all three blocks in sequence
run_block 1 3 10 2 13    # iterations 1–3: coarse cone ±20°, lp ~33 Å
run_block 4 3  5 3 17    # iterations 4–6: medium cone ±15°, lp ~25 Å
run_block 7 3  3 3 22    # iterations 7–9: fine cone ±9°,   lp ~20 Å

echo "Done. subtomo_param.star written to ${rootdir}/${param_name}"
echo "Final motl after all 9 iterations will be: lists/motl_10.star"
echo "Final reference will be: ref/ref_class1_10.mrc"
