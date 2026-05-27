#!/usr/bin/env python3
"""
Patch e2spt_pcasplit.py in the active conda env: replace np.int with np.int64.
Safe to run multiple times — checks before patching.
"""
import shutil
import os
import sys

script_path = shutil.which("e2spt_pcasplit.py")
if script_path is None:
    print("ERROR: e2spt_pcasplit.py not found on PATH. Is the eman2 conda env active?")
    sys.exit(1)

with open(script_path, "r") as f:
    content = f.read()

if "r = r.astype(np.int)" not in content:
    print(f"No patch needed: {script_path}")
    sys.exit(0)

backup = script_path + ".bak"
if not os.path.exists(backup):
    shutil.copy2(script_path, backup)
    print(f"Backup: {backup}")

new_content = content.replace("r = r.astype(np.int)", "r = r.astype(np.int64)")
with open(script_path, "w") as f:
    f.write(new_content)

print(f"Patched: {script_path}  (np.int → np.int64)")
