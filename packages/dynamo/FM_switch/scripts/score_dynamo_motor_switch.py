#!/usr/bin/env python3
"""
Score Dynamo dpkpca predictions for motor_switch k=2.

Usage:
  conda run -n relion-5.0 python3 packages/dynamo/FM_switch/scripts/score_dynamo_motor_switch.py
"""
import os, subprocess

GT    = ("/home/jblaser2/Research/synthetic_sta/motor_switch/"
         "production_5apix/subtomos/all_particles_aligned/labels.csv")
PRED  = ("packages/dynamo/dynamo_outputs/motor_switch_pca/predictions_k2.csv")
STA   = "/home/jblaser2/Research/STA"

cmd = [
    "conda", "run", "-n", "relion-5.0",
    "python3", "scripts/eval/score_synthetic.py",
    "--pred", PRED,
    "--gt",   GT,
    "--package", "dynamo",
    "--k", "2",
    "--dataset", "motor_switch",
    "--run", "k2_pca_motor_switch",
]
print("Running:", " ".join(cmd))
subprocess.check_call(cmd, cwd=STA)
