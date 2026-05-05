# Recommended Standardized Benchmark Workflow

For fair cross-package classification benchmarking:

1. Normalize all subtomograms
2. Ensure identical voxel sizes
3. Ensure identical box dimensions
4. Use identical particle ordering
5. Avoid package-specific preprocessing initially
6. Export all package inputs from the same master dataset
7. Keep a master particle index mapping

Recommended master files:
```
master_particles.csv
master_particles.star
master_particles.json
```

containing:

- particle ID
- source filename
- class label
- coordinates
- alignment transform
- voxel size
- tomogram ID

This prevents indexing mismatches across packages.

--------
I created a full set of conversion/preparation scripts for:


RELION


EMAN2


Dynamo


STOPGAP


emClarity


Warp / M


including:


.mrc → .mrcs stack generation


.mrc → .em conversion


STAR file generation


motive list generation


normalization scripts


SLURM batch example


standardized benchmarking workflow recommendations


The scripts are designed specifically for aligned subtomogram classification benchmarking across packages.
