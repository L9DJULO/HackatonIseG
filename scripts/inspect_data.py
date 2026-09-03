"""T0.1 — Inspection brute des données iSeg-2017. Ne suppose rien, vérifie tout."""
import sys
from pathlib import Path

import nibabel as nib
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
TRAIN = ROOT / "iSeg-2017-Training"
TEST = ROOT / "iSeg-2017-Testing"


def load(path_hdr: Path) -> tuple[np.ndarray, tuple, str]:
    img = nib.load(str(path_hdr))
    arr = np.asarray(img.dataobj)
    return arr, tuple(float(z) for z in img.header.get_zooms()), str(arr.dtype)


def main() -> None:
    print(f"nibabel image class for subject-1-T1: {type(nib.load(str(TRAIN / 'subject-1-T1.hdr'))).__name__}")
    print()
    print("subject | mod  | shape            | dtype   | spacing (mm)      | min    | max    | nonzero%")
    for sid in range(1, 11):
        for mod in ("T1", "T2", "label"):
            arr, zooms, dt = load(TRAIN / f"subject-{sid}-{mod}.hdr")
            nz = 100.0 * np.count_nonzero(arr) / arr.size
            print(f"{sid:7d} | {mod:5s}| {str(arr.shape):17s}| {dt:8s}| {str(tuple(round(z,3) for z in zooms)):18s}| {arr.min():7.1f}| {arr.max():7.1f}| {nz:6.2f}")
    print()
    print("Label values and proportions (train):")
    for sid in range(1, 11):
        lab, _, _ = load(TRAIN / f"subject-{sid}-label.hdr")
        vals, counts = np.unique(lab, return_counts=True)
        inside = counts[vals != 0].sum()
        props = {int(v): round(float(c) / inside, 3) for v, c in zip(vals, counts) if v != 0}
        print(f"  subject-{sid}: values={vals.tolist()} inside-brain proportions={props}")
    print()
    print("Mask agreement: (T1 != 0) vs (label != 0) vs (T2 != 0)")
    print("subject | T1!=0 vox | label!=0 vox | T1&label | T1 only | label only | agree% | T2!=0 vox")
    for sid in range(1, 11):
        t1, _, _ = load(TRAIN / f"subject-{sid}-T1.hdr")
        t2, _, _ = load(TRAIN / f"subject-{sid}-T2.hdr")
        lab, _, _ = load(TRAIN / f"subject-{sid}-label.hdr")
        m1, ml, m2 = t1 != 0, lab != 0, t2 != 0
        inter = m1 & ml
        union = m1 | ml
        print(f"{sid:7d} | {m1.sum():9d} | {ml.sum():12d} | {inter.sum():8d} | {(m1 & ~ml).sum():7d} | {(ml & ~m1).sum():10d} | {100*inter.sum()/union.sum():6.2f} | {m2.sum():9d}")
    print()
    print("Intensity stats inside (label != 0), per tissue, subject-1 and subject-5:")
    for sid in (1, 5):
        t1, _, _ = load(TRAIN / f"subject-{sid}-T1.hdr")
        t2, _, _ = load(TRAIN / f"subject-{sid}-T2.hdr")
        lab, _, _ = load(TRAIN / f"subject-{sid}-label.hdr")
        for v, name in ((10, "CSF"), (150, "GM"), (250, "WM")):
            sel = lab == v
            print(f"  subject-{sid} {name}: T1 mean={t1[sel].mean():7.1f} sd={t1[sel].std():6.1f} | T2 mean={t2[sel].mean():7.1f} sd={t2[sel].std():6.1f}")
    print()
    print("Test subjects:")
    for sid in range(11, 24):
        p = TEST / f"subject-{sid}-T1.hdr"
        if not p.exists():
            print(f"  subject-{sid}: MISSING")
            continue
        arr, zooms, dt = load(p)
        print(f"  subject-{sid}: shape={arr.shape} dtype={dt} spacing={tuple(round(z,3) for z in zooms)} max={arr.max()}")
    print()
    print("Header orientation / affine (subject-1-T1):")
    img = nib.load(str(TRAIN / "subject-1-T1.hdr"))
    print(np.round(img.affine, 3))
    print("Extra hdr fields with data:", {k: img.header[k] for k in ("datatype", "bitpix", "scl_slope", "scl_inter") if k in img.header})


if __name__ == "__main__":
    main()
