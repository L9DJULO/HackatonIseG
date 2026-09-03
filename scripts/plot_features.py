"""Figure qualitative : coupe axiale de T1, T2, label et d'un échantillon de features par bloc.

Usage : python scripts/plot_features.py <subject_id> [slice_index]  -> figures/features_subject-<id>.png
"""
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.features.registry import build_extractor  # noqa: E402
from src.io import load_subject, mask_to_volume  # noqa: E402

SHOWN = [
    "intensity/t1t2_ratio", "intensity/t1_pct",
    "gaussian/t1_s1_gradmag", "gaussian/t2_s2_hess_e3", "gaussian/t1_s4_lap", "gaussian/t1_dog_2_4",
    "spatial/dist_border", "spatial/dist_midsag",
    "morpho/t1_tos_depth", "morpho/t1_tos_a1000_compact", "morpho/t2_tophat_black_a500", "morpho/t1_tos_height",
    "symmetry/t1_mirror_diff", "context/t1_r2_std",
]


def main(subject_id: int, k: int | None = None) -> None:
    s = load_subject(subject_id, ROOT / "data")
    ext = build_extractor(["intensity", "gaussian", "spatial", "morpho", "symmetry", "context"], cache_dir=ROOT / "cache", verbose=False)
    X = ext.transform(s)
    names = ext.names
    zs = np.flatnonzero(s.mask.any(axis=(0, 1)))
    k = k if k is not None else int(zs[len(zs) // 2])
    panels = [("T1", s.t1), ("T2", s.t2)]
    if s.label is not None:
        panels.append(("label", s.label.astype(np.float32)))
    for n in SHOWN:
        if n in names:
            panels.append((n, mask_to_volume(np.asarray(X[:, names.index(n)]), s.mask, fill=np.nan)))
    ncol = 6
    nrow = int(np.ceil(len(panels) / ncol))
    fig, axes = plt.subplots(nrow, ncol, figsize=(3.2 * ncol, 3.4 * nrow))
    for ax, (title, vol) in zip(axes.ravel(), panels):
        sl = vol[:, :, k].T
        ax.imshow(np.ma.masked_invalid(sl), cmap="gray" if title in ("T1", "T2") else "viridis", origin="lower")
        ax.set_title(title, fontsize=9)
        ax.axis("off")
    for ax in axes.ravel()[len(panels):]:
        ax.axis("off")
    out = ROOT / "figures" / f"features_subject-{subject_id}.png"
    out.parent.mkdir(exist_ok=True)
    fig.tight_layout()
    fig.savefig(out, dpi=110)
    print(out)


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 1, int(sys.argv[2]) if len(sys.argv) > 2 else None)
