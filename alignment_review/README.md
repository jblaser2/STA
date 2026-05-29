# Alignment Review

Manual visual inspection of all 672 T4P subtomograms to confirm alignment quality.

## Results summary

| Verdict | Count |
|---------|-------|
| Good (aligned) | 664 |
| NOT aligned | 1 |
| Other (flagged with notes) | 7 |

Full details: [`alignment_review_results.txt`](alignment_review_results.txt)  
Full per-particle record: [`alignment_review_progress.json`](alignment_review_progress.json)

## Method

Each subtomogram was displayed as three orthogonal **average-projection slabs** (10 slices
averaged around the central Z, Y, and X planes) to improve SNR. A green crosshair overlay marks
the box center. Particles were judged aligned if the density appeared centered on the crosshair
across all three views.

## How to re-run the reviewer

Requires `mrcfile` and `matplotlib` (available in the `pytom_env` conda environment).

```bash
conda activate pytom_env
# or, without activating:
~/conda-envs/pytom_env/bin/python3 STA/alignment_review/review_alignment.py
```

The script automatically skips already-reviewed particles and picks up where you left off.

### Controls

| Key | Action |
|-----|--------|
| `Y` / Enter | Mark as **aligned** (good) |
| `N` | Mark as **NOT aligned** |
| `O` | Mark as **Other** — type a free-text note, then Enter |
| `B` / Left arrow | Go back and re-judge the previous particle |
| `S` | Skip for now (moved to end of queue) |
| `Q` | Quit and save progress |

On-screen buttons mirror all controls.

### Re-reviewing specific particles

To send a particle back into the review queue, edit `alignment_review_progress.json`:
remove its entry from `"reviewed"` and add its filename to the `"skipped"` list, then re-run.
