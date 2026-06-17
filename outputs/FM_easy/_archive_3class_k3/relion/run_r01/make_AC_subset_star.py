#!/usr/bin/env python3
"""Subset particles_wedge.star to the A+C particles; write absolute CTF paths."""
import csv, os
RUN = os.path.dirname(os.path.abspath(__file__))
PAIR = os.path.expanduser("~/Research/STA/packages/dynamo/dynamo_outputs/easy_pair_AC/pair_labels.csv")
ACfiles = {r['orig_file'] for r in csv.DictReader(open(PAIR))}   # subtomo_XXXX.mrc names
print(f"A+C target files: {len(ACfiles)}")

src = os.path.join(RUN, "particles_wedge.star")
dst = os.path.join(RUN, "particles_wedge_AC.star")
ctf_abs = os.path.join(RUN, "ctf", "wedge_ctf.mrc")
assert os.path.exists(ctf_abs), ctf_abs

out, kept, in_particles = [], 0, False
for line in open(src):
    s = line.strip()
    if s.startswith("data_particles"): in_particles = True
    is_data = s.startswith("/") and "subtomo_" in s
    if is_data:
        parts = s.split()
        base = os.path.basename(parts[0])
        if base in ACfiles:
            parts[1] = ctf_abs               # absolute ctf path
            out.append(" ".join(parts) + "\n")
            kept += 1
    else:
        out.append(line)
open(dst, "w").writelines(out)
print(f"kept {kept} particles -> {dst}")
