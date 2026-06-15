#!/usr/bin/env python3
"""Train OPUS-ET with the in-training subtomogram orientation search DISABLED.

WHY THIS EXISTS
---------------
By default the decoder (`cryodrgn.models.VanillaDecoder.forward`) re-aligns every
subtomogram on every training step: it builds a local Hopf grid of candidate
orientations (`get_particle_hopfs`) and marginalises the reconstruction loss over
them with a softmax-EM weighting (`train_tomo.loss_function`, the `C > 1` branch).
This happens regardless of the input poses, so an already-aligned dataset (all
Euler angles = 0,0,0) is re-searched needlessly. That wastes compute and lets
orientation soak up variance that should instead land in the latent code, blurring
the classification.

This wrapper monkeypatches `get_particle_hopfs` so it returns ONLY the seed
orientation (the input pose). With a single candidate the marginalisation
degenerates to `C = 1` and the loss falls through to the plain-MSE branch
(`train_tomo.loss_function`, line ~428) -- i.e. no pose search. The opusTomo
source tree is left untouched; the patch lives entirely here.

NOTE ON THE RESIDUAL IN-PLANE SPIN
----------------------------------
A random in-plane angle (`rand_ang`) is still drawn each step, but it is applied
*identically* to the reference image and to the template projection, so the loss
compares like-for-like at a random viewing azimuth -- matched augmentation, not a
search. It cannot let pose explain heterogeneity. Fully removing it would require
editing `VanillaDecoder.forward` (a 2-line source change), which we deliberately
avoid here.

USAGE
-----
Identical CLI to `dsd train_tomo` -- this just wraps it:

    python train_skipalign.py <particles.star> --poses ... -o ... [all train_tomo args]
"""

import argparse
import sys

# Import the model module first so the class exists before we patch it.
import cryodrgn.models as models
from cryodrgn.commands import train_tomo


def _install_skip_align_patch():
    """Collapse the decoder's local orientation grid to the single seed pose."""
    orig = models.VanillaDecoder.get_particle_hopfs

    def get_particle_hopfs_nosearch(self, coords, hp_order=64, depth=2):
        # `coords` are hopf euler pairs (N, 2): the seed orientation(s).
        # Return TWO copies of the seed -> two *identical* candidate orientations.
        #
        # Why two and not one: opusTomo's loss_function only defines `snr` inside
        # its `C > 1` branch but uses it unconditionally afterwards, so a true
        # C==1 crashes with UnboundLocalError. With two identical candidates the
        # softmax-EM marginalisation is a no-op (uniform weights -> same loss and
        # gradient as a single orientation), but the C>1 branch runs and defines
        # snr. Net effect: still no orientation search.
        return coords[:1, :2].repeat(2, 1).contiguous()

    models.VanillaDecoder.get_particle_hopfs = get_particle_hopfs_nosearch
    models.VanillaDecoder._get_particle_hopfs_orig = orig  # keep a handle, just in case
    print("[skip-align] VanillaDecoder.get_particle_hopfs patched: "
          "in-training orientation search DISABLED (C=1, fixed input poses).")


def main():
    _install_skip_align_patch()
    parser = argparse.ArgumentParser(description=train_tomo.__doc__)
    train_tomo.add_args(parser)
    args = parser.parse_args()
    train_tomo.main(args)


if __name__ == "__main__":
    sys.exit(main())
