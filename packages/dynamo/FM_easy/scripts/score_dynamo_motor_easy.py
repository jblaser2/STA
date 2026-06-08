#!/usr/bin/env python3
"""Score Dynamo motor_easy predictions (HAC or PCA) against GT. Run from ~/Research/STA."""
import os, sys, subprocess, argparse

ap = argparse.ArgumentParser()
ap.add_argument("--outdir", default=os.path.expanduser(
    "~/Research/STA/packages/dynamo/dynamo_outputs/motor_easy_hac"))
ap.add_argument("--run_suffix", default="hac_cnew")
args = ap.parse_args()

OUT_DIR = os.path.expanduser(args.outdir)
GT      = os.path.expanduser(
    "~/Research/synthetic_sta/motor_easy/production/subtomos/merged_all_aln/labels.csv")
PYTHON  = os.path.expanduser("~/conda-envs/eman2/bin/python3")
SCORE   = os.path.expanduser("~/Research/STA/scripts/eval/score_synthetic.py")

for k in [2, 3]:
    pred = os.path.join(OUT_DIR, f"predictions_k{k}.csv")
    if not os.path.exists(pred):
        print(f"k={k}: {pred} not found, skipping")
        continue
    run_name = f"k{k}_{args.run_suffix}"
    result = subprocess.run(
        [PYTHON, SCORE, "--pred", pred, "--gt", GT,
         "--package", "dynamo", "--k", str(k), "--run", run_name],
        capture_output=True, text=True, cwd=os.path.expanduser("~/Research/STA")
    )
    print(result.stdout.strip())
    if result.stderr:
        print(result.stderr.strip(), file=sys.stderr)
