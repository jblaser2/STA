#!/usr/bin/env python3
"""
extract_pytom_classes.py — extract per-particle class assignments from a
PyTom classified ParticleList XML and write predictions.csv (file, pred_label).

Usage:
  python3 scripts/eval/extract_pytom_classes.py \
    --xml PyTom/autofocus_v2mask_k2/classified_pl_iter14.xml \
    --out results/pytom_v2mask_k2.csv
"""
import argparse
import csv
import os
import xml.etree.ElementTree as ET
from collections import Counter


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--xml", required=True,
                    help="PyTom classified ParticleList XML (classified_pl_iter{N}.xml)")
    ap.add_argument("--out", required=True, help="Output predictions CSV")
    ap.add_argument("--last-iter", action="store_true",
                    help="If --xml is a directory, find and use the highest-numbered iter XML")
    args = ap.parse_args()

    xml_path = args.xml
    if args.last_iter or os.path.isdir(xml_path):
        import glob
        xmls = sorted(glob.glob(os.path.join(xml_path, "classified_pl_iter*.xml")),
                      key=lambda p: int(os.path.basename(p)
                                         .replace("classified_pl_iter", "")
                                         .replace(".xml", "")))
        if not xmls:
            raise SystemExit(f"No classified_pl_iter*.xml found in {xml_path}")
        xml_path = xmls[-1]
        print(f"Using last iter: {xml_path}")

    tree = ET.parse(xml_path)
    particles = tree.findall(".//Particle")
    if not particles:
        raise SystemExit(f"No <Particle> elements found in {xml_path}")

    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    rows = []
    for p in particles:
        fname = os.path.basename(p.attrib.get("Filename", ""))
        class_el = p.find("Class")
        cls = class_el.attrib.get("Name", "?") if class_el is not None else "?"
        rows.append((fname, cls))

    with open(args.out, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["file", "pred_label"])
        w.writerows(rows)

    counts = Counter(c for _, c in rows)
    print(f"Wrote {len(rows)} predictions -> {args.out}")
    print(f"Class distribution: {dict(sorted(counts.items()))}")


if __name__ == "__main__":
    main()
