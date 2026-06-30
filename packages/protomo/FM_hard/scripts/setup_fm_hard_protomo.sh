#!/bin/bash
# ProTomo FM_hard setup: create workspace, convert mask, build dataset.i3i.
# Run from STA repo root.
set -e
source ~/Applications/protomo-3.1.0/setup.sh

PARTICLES="$HOME/Research/synthetic_sta/motor_hard/subtomos/merged_ABC_full"
MASK_MRC="$HOME/Research/synthetic_sta/motor_hard/maps/diff_mask_hard.mrc"
WORKSPACE="$HOME/Research/protomo/motor_hard"
PREPARE="$WORKSPACE/prepare"
PROCESS="$WORKSPACE/process"
STACKS="$PREPARE/stacks"

mkdir -p "$PREPARE" "$PROCESS" "$STACKS"

log() { echo "[$(date '+%H:%M:%S')] $*"; }

# 1. Symlink particle MRC files into stacks/
log "Symlinking particles..."
for f in "$PARTICLES"/subtomo_*.mrc; do
    fn=$(basename "$f")
    [ -L "$STACKS/$fn" ] || ln -sf "$f" "$STACKS/$fn"
done
echo "  $(ls "$STACKS"/*.mrc 2>/dev/null | wc -l) stacks linked"

# 2. Write dataset.prep
log "Writing dataset.prep..."
PREP="$PREPARE/dataset.prep"
{ echo "search stacks"; echo ""; for f in "$PARTICLES"/subtomo_*.mrc; do echo "attach $(basename "$f")"; done; echo ""; echo "save dataset.i3i"; } > "$PREP"

# 3. Run tomoprepare to build dataset.i3i
log "Running tomoprepare..."
cd "$PREPARE"
DATADIR="$STACKS" tomoprepare dataset.prep 2>&1 | tee tomoprepare.log
[ -f dataset.i3i ] || { echo "ERROR: dataset.i3i not created"; exit 1; }
log "  dataset.i3i created"

# 4. Convert diff_mask_hard.mrc -> mask_diff.i3i
log "Converting diff_mask_hard.mrc -> mask_diff.i3i..."
TMPDIR="$(mktemp -d)" && trap "rm -rf $TMPDIR" EXIT
# i3cut reads MRC, writes i3i; use conda eman2 mrcfile for normalization
~/miniforge3/bin/conda run -n eman2 python3 -c "
import mrcfile, numpy as np, shutil, os
with mrcfile.open('$MASK_MRC', permissive=True) as m:
    d = m.data.astype(np.float32)
    apix = float(m.voxel_size.x)
with mrcfile.new('$TMPDIR/mask.mrc', overwrite=True) as m:
    m.set_data(d); m.voxel_size = apix
print('mask shape:', d.shape, 'nonzero:', (d>0.1).sum())
"
i3cut -slice "0 0 -1 1 0 0" "$TMPDIR/mask.mrc" "$PREPARE/mask_diff.i3i" 2>&1 || \
    cp "$MASK_MRC" "$PREPARE/mask_diff.mrc" && \
    i3cut -slice "0 0 -1 1 0 0" "$PREPARE/mask_diff.mrc" "$PREPARE/mask_diff.i3i" 2>&1 || true
[ -f "$PREPARE/mask_diff.i3i" ] && log "  mask_diff.i3i created" || log "  WARNING: mask conversion may have failed"

log "Setup complete. Next: run run_fm_hard_protomo.sh from process/"
