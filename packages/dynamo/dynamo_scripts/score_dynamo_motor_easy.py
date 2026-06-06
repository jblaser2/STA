#!/usr/bin/env python3
"""Score Dynamo HAC motor_easy predictions against GT. Run from ~/Research/STA."""
import os, sys, subprocess

OUT_DIR = os.path.expanduser("~/Research/STA/dynamo/dynamo_outputs/motor_easy_hac")
GT      = os.path.expanduser(
    "~/Research/synthetic_sta/motor_easy/production/subtomos/merged_all_aln/labels.csv")
PYTHON  = os.path.expanduser("~/conda-envs/eman2/bin/python3")
SCORE   = os.path.expanduser("~/Research/STA/scripts/eval/score_synthetic.py")

for k in [2, 3]:
    pred = os.path.join(OUT_DIR, f"predictions_k{k}.csv")
    if not os.path.exists(pred):
        print(f"k={k}: {pred} not found, skipping")
        continue
    result = subprocess.run(
        [PYTHON, SCORE, "--pred", pred, "--gt", GT,
         "--package", "dynamo", "--k", str(k), "--run", f"hac_k{k}_cnew"],
        capture_output=True, text=True, cwd=os.path.expanduser("~/Research/STA")
    )
    print(result.stdout.strip())
    if result.stderr:
        print(result.stderr.strip(), file=sys.stderr)
