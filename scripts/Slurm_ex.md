# SLURM Batch Example

### Script: run_conversion.slurm

```bash
#!/bin/bash

#SBATCH --job-name=subtomo_convert
#SBATCH --time=02:00:00
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=32G
#SBATCH --output=convert_%j.out

module load python

source ~/miniconda3/etc/profile.d/conda.sh
conda activate cryoet

python prepare_stopgap.py
```

