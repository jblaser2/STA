#!/bin/sh
# param-template.sh — FM_hard (813 GT-aligned particles, 96^3, k=3, no junk)
# Derived from motor_easy_hc. Same box, same band, k=3 classes.

export DATADIR="/home/jblaser2/Research/protomo/motor_hard/prepare/stacks"
export DIRPRFX="cycle-"
export CYCPRFX="fmh-"

export MOTIFSIZE="96 96 96"
export WDGCOMP="false"

export REFIMG=
export REFSEL="0-2"
export REFMSKOPT1="elliptic 45 45 45 apod 5 5 5"
export REFMSKOPT2=
export REFMSKOPT3=
export REFMOLMSK=
export REFMONT="true"

export MRAMSKOPT1="elliptic 45 45 45 apod 5 5 5"
export MRAMSKOPT2=
export MRAMSKOPT3=
export MRAMOLMSK=
export MRAAREA=0.0

export LOWPASS=" 0.400 0.400 0.400 apod 0.050 0.050 0.050"
export HIGHPASS="0.060 0.060 0.060 apod 0.007 0.007 0.007"
export FOUGAUSS=

export MRACC="xcf"
export MRAPKR="0 0 0"
export MRALIMIT=
export MRASTEPS=
export MRAAVG="true"

export MSAIMGSIZE="96 96 96"
export MSAMASK="/home/jblaser2/Research/protomo/motor_hard/prepare/mask_diff.i3i"
export MSAMASKTHR=
export MSAMSKOPT1=
export MSAMSKOPT2=

export MSANBFACT="813"
export MSAFACT="20"
export MSAVAR="0.0"

export CLASSES="3"
export CLSHACONN="ward"
export CLSHVO=
export CLSHVM=
export CLSMONT="0.4"

export SELNR=3
export SELAVG="0-2"
export SELMSKOPT1="${MRAMSKOPT1}"
export SELMSKOPT2=
export SELMSKOPT3=
export SELMOLMSK=
export SELAREA=${MRAAREA}
export SELLOWPASS="${LOWPASS}"
export SELHIGHPASS="${HIGHPASS}"
export SELFOUGAUSS="${FOUGAUSS}"
export SELCC="xcf"
export SELMONT="true"
export SELPKR="5 5 5"
export SELLIMIT=
export SELSTEPS=

export FSCMSKOPT1="elliptic 31 31 31 apod 5 5 5"
export FSCMSKOPT2=
export FSCMSKOPT3=
export FSCCLASS="false"

export CYCLOG="true"
export GLBLAVG="false"
export YPERM="true"
export CYCDBG="false"
