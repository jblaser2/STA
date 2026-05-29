#!/bin/sh
#
# subvolparam.sh  version 1.0  define processing parameters
#

#
# General parameters
#
# location of original stacks
export DATADIR="../prepare/stacks"

# prefix of directory names of alignment cycles
export DIRPRFX="cycle-"

# prefix of output file names
export CYCPRFX="hst-"

# size of subvolumes
export MOTIFSIZE="84 64 72"

# missing wedge compensation
export WDGCOMP="false"


#
# Parameters for raw motif alignment
#
#
# reference image or image stack (leave blank to use the global average)
export REFIMG=

# if REFIMG is set to "classaverages", use aligned class averages 
# of previous cycle with class selection REFSEL
export REFSEL="1-3"

# masks applied to reference
# rectangular x y z [apod x y z] for rectangular mask
# elliptic x y z [apod x y z] for ellipsoidal mask
# gaussian x y z for Gaussian mask
export REFMSKOPT1="rectangular 37 37  0 apod 7 7 0"
export REFMSKOPT2="rectangular  0  0 61 apod 0 0 7"
export REFMSKOPT3=
# molecular mask file name, image size must be equal to MOTIFSIZE,
# leave blank for no mask
export REFMOLMSK=

# montages (true or false)
export REFMONT="true"
# number of columns in montage
#export REFMONTCOL="10"

# multireference alignment mask, applied to raw motifs
# rectangular x y z [apod x y z] for rectangular mask
# elliptic x y z [apod x y z] for ellipsoidal mask
# gaussian x y z for Gaussian mask
export MRAMSKOPT1="elliptic 45 45 0 apod 7 7 0"
export MRAMSKOPT2=
export MRAMSKOPT3=
# molecular mask file name, image size must be equal to MOTIFSIZE,
# leave blank for no mask
export MRAMOLMSK=
# overlap area
export MRAAREA=0.8

# Fourier space filters
export LOWPASS=" 0.400 0.400 0.400 apod 0.050 0.050 0.050"
export HIGHPASS="0.060 0.060 0.060 apod 0.007 0.007 0.007"
export FOUGAUSS=

# cross-correlation mode: xcf mcf pcf dbl (leave blank for xcf)
export MRACC="xcf"

# peak search radius
export MRAPKR="5 5 5"

# radius for center of mass calculation
# export MRACMR="2 2 2"

# grid search
# * for translational alignment only, leave blank"
# * for rotational alignment, use limit <nut> <spin> and steps <nstep> <sstep>
# search direction of rotation axis in concentric cones with maximum
# half-angle <nut> (nutation angle) in angular steps of <nstep> degrees
# search rotation about the above axis from -<spin> to +<spin> (spin angle)
# in angular steps of <sstep> degrees
# * rotational alignment about z-axis only:set <nut> and <nstep> to zero"
# angular ranges: 0 <= <spin> <= 180;  0 <= <nut> <= 180
export MRALIMIT="0 180"
export MRASTEPS="0 180"

# global average of aligned images
export MRAAVG="true"


#
# MSA parameters
#
# size of extracted subvolumes for MSA
export MSAIMGSIZE="24 24 36"

# MSA mask options
# file name of MSA mask, image density range must be from 0 to 1
# size must be defined above with MSAIMGSIZE
# only pixels above the threshold value MSAMASKTHR are selected
# (leave blank to use no mask, or set to "opt" to use options below)
export MSAMASK=opt
export MSAMASKTHR=

# rectangular x y z for rectangular mask
# elliptic x y z for ellipsoidal mask
export MSAMSKOPT1="elliptic 21 21 0"
export MSAMSKOPT2="rectangular 0 0 33"
export MSAMSKOPT3=

# file name of image to superimpose mask for visualization,
# for example a global average
# (leave blank to skip, or set to "avg" to use global average)
export MSAMASKSUPERPOS=avg

# image mask applied to motifs
export MSAIMGMSKOPT1="elliptic 45 45 0 apod 7 7 0"
export MSAIMGMSKOPT2=
export MSAIMGMSKOPT3=

# Fourier space filters to prepare data for MSA
export MSALOWPASS=" 0.400 0.400 0.400 apod 0.050 0.050 0.050"
export MSAHIGHPASS="0.060 0.060 0.060 apod 0.007 0.007 0.007"

# Maximal number of factors
export MSAFACT=40

# Variance image
export MSAVAR="true"

# montage of eigenimages (true or false)
export MSAMONT="true"


#
# Classification parameters
#
# classifications with various number of classes to generate
# (single number or list of numbers separated by spaces)
# must be covered by the range specified with parameters CLSMIN, CLSMAX, CLSINC
export CLASSES="4 8"

# min/max number and increment of classes to be stored in the output file
# the settings below store 2 4 6 8 classes
export CLSMIN="2"
export CLSMAX="8"
export CLSINC="2"

# factors used in classification
# (comma separated list, no spaces)
export CLSFACT="1-4"

# fraction of ignored high-variance outliers
export CLSHVO="0.1"

# fraction of ignored high-variance class members
export CLSHVM="0.1"

# low-pass filter for montaged class averages (leave blank to skip montage)
export CLSMONT="0.4"


#
# Parameters for class average alignment
#

# classification with SELNR classes to align
export SELNR=4

# select averages of above classification
# e.g. for an 8-class classification, class numbers 0 - 7
# are regular averages, class number 8 is a junk class containing
# excluded images (see parameters CLSHVO and CLSHVM above)
export SELAVG="0-3"

# masks applied to class averages
# rectangular x y z [apod x y z] for rectangular mask
# elliptic x y z [apod x y z] for ellipsoidal mask
# gaussian x y z for Gaussian mask
export SELMSKOPT1="${MRAMSKOPT1}"
export SELMSKOPT2="${MRAMSKOPT2}"
export SELMSKOPT3="${MRAMSKOPT3}"
# molecular mask file name, image size must be equal to MOTIFSIZE,
# leave blank for no mask
export SELMOLMSK="${MRAMOLMSK}"
# overlap area
export SELAREA=${MRAAREA}

# Fourier space filters
export SELLOWPASS="${LOWPASS}"
export SELHIGHPASS="${HIGHPASS}"
export SELFOUGAUSS="${FOUGAUSS}"

# cross-correlation mode: xcf mcf pcf dbl (leave blank for xcf)
export SELCC="xcf"

# montages (true or false)
export SELMONT="true"

# peak search radius
export SELPKR="5 5 15"

# radius for center of mass calculation
# export SELCMR="2 2 2"

# grid search
# * for translational alignment only, leave blank"
# * for rotational alignment, use limit <nut> <spin> and steps <nstep> <sstep>
# search direction of rotation axis in concentric cones with maximum
# half-angle <nut> (nutation angle) in angular steps of <nstep> degrees
# search rotation about the above axis from -<spin> to +<spin> (spin angle)
# in angular steps of <sstep> degrees
# * rotational alignment about z-axis only:set <nut> and <nstep> to zero"
# angular ranges: 0 <= <spin> <= 180;  0 <= <nut> <= 180
export SELLIMIT="0 180"
export SELSTEPS="0 180"


#
# Fourier shell correlation
#
# masks applied to averages (leave blank to skip FSC)
# rectangular x y z for rectangular mask
# elliptic x y z for ellipsoidal mask
export FSCMSKOPT1="elliptic 31 31 0 apod 7 7 0"
export FSCMSKOPT2="rectangular 0 0 61 apod 0 0 7"
export FSCMSKOPT3=

# compute FSC of class averages
export FSCCLASS="false"


#
# miscellaneous parameters
#
# print messages
export CYCLOG="true"

# produce global average
export GLBLAVG="false"

# produce side views of averages
export YPERM="true"

# write some intermediate results for debugging
export CYCDBG="false"
