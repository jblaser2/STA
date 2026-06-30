#!/usr/bin/env python3
"""Set up Dynamo dpkpca for FM_hard (813p, 96^3, 3 classes)."""
import os, csv
ALN   = os.path.expanduser(
    "~/Research/synthetic_sta/motor_hard/subtomos/merged_ABC_full")
OUT   = os.path.expanduser(
    "~/Research/STA/packages/dynamo/dynamo_outputs/motor_hard_pca")
DATA  = os.path.join(OUT, "data")
os.makedirs(DATA, exist_ok=True)

# Remove stale symlinks
for f in os.listdir(DATA):
    if f.endswith(".mrc"):
        os.remove(os.path.join(DATA, f))

rows = list(csv.DictReader(open(os.path.join(ALN, "labels.csv"))))
print(f"FM_hard: {len(rows)} particles  "
      + "  ".join(f"{lbl}:{sum(r['label']==lbl for r in rows)}"
                  for lbl in ['base','basal_body','mature']))

lbl_path = os.path.join(OUT, "labels.csv")
tbl_path = os.path.join(OUT, "motor_hard_pca.tbl")
with open(lbl_path, "w", newline="") as lf, open(tbl_path, "w") as tf:
    w = csv.writer(lf)
    w.writerow(["tag", "orig_file", "gt_label"])
    for i, r in enumerate(rows):
        tag = i + 1
        os.symlink(os.path.join(ALN, r["file"]),
                   os.path.join(DATA, f"particle_{tag:05d}.mrc"))
        w.writerow([tag, r["file"], r["label"]])
        row = [0.0] * 35; row[0] = tag; row[1] = 1; row[5] = 1
        tf.write(" ".join(
            str(int(v) if v == int(v) else v) for v in row) + "\n")

print(f"Data symlinks: {DATA}")
print(f"Table: {tbl_path}")
print(f"Labels: {lbl_path}")
