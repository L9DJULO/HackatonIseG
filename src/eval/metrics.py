"""Métriques officielles iSeg-2017 : Dice, ASD (average surface distance), MHD.

Toutes les métriques sont calculées PAR CLASSE et PAR SUJET, jamais agrégées sur les
voxels de plusieurs sujets. Le fond (classe 0) n'est jamais évalué.

Distances de surface : on prend les voxels de frontière de chaque masque (masque moins
son érosion 6-connexe), et on lit la transformée de distance euclidienne du complémentaire
de l'autre masque en ces voxels (scipy.ndimage.distance_transform_edt, avec le spacing).

MHD : le challenge iSeg-2017 (Wang et al., IEEE TMI 2019) rapporte une "modified Hausdorff
distance" ; deux définitions circulent, on implémente les deux :
- "p95"  : 95e percentile des distances de surface symétriques (défaut, c'est celle des
           tableaux du challenge) ;
- "dubuisson" : max des deux distances directionnelles MOYENNES (Dubuisson & Jain 1994).
"""
from __future__ import annotations

from typing import Iterable

import numpy as np
from scipy import ndimage

from src.io import CLASS_NAMES, TISSUE_CLASSES


def dice(pred: np.ndarray, gt: np.ndarray) -> float:
    """Dice de deux masques booléens. 1.0 si les deux sont vides."""
    pred = pred.astype(bool)
    gt = gt.astype(bool)
    denom = pred.sum() + gt.sum()
    if denom == 0:
        return 1.0
    return float(2.0 * np.logical_and(pred, gt).sum() / denom)


def _surface(mask: np.ndarray) -> np.ndarray:
    """Voxels de frontière : dans le masque et ayant au moins un 6-voisin hors masque."""
    if not mask.any():
        return mask
    struct = ndimage.generate_binary_structure(mask.ndim, 1)
    return mask & ~ndimage.binary_erosion(mask, structure=struct, border_value=0)


def _crop_union(a: np.ndarray, b: np.ndarray, margin: int = 2) -> tuple[slice, ...]:
    """Boîte englobante de a | b avec marge : les EDT n'ont pas besoin du volume entier."""
    union = a | b
    sl = []
    for axis in range(union.ndim):
        proj = np.any(union, axis=tuple(i for i in range(union.ndim) if i != axis))
        nz = np.flatnonzero(proj)
        sl.append(slice(max(nz[0] - margin, 0), min(nz[-1] + margin + 1, union.shape[axis])))
    return tuple(sl)


def surface_distances(
    pred: np.ndarray, gt: np.ndarray, spacing: Iterable[float] = (1.0, 1.0, 1.0)
) -> tuple[np.ndarray, np.ndarray]:
    """Retourne (d_pred_to_gt, d_gt_to_pred) : distances des voxels de surface de l'un à l'autre."""
    pred = pred.astype(bool)
    gt = gt.astype(bool)
    spacing = tuple(float(s) for s in spacing)
    if not pred.any() or not gt.any():
        inf = np.array([np.inf], dtype=np.float64)
        return inf, inf
    crop = _crop_union(pred, gt)
    pred, gt = pred[crop], gt[crop]
    dt_gt = ndimage.distance_transform_edt(~gt, sampling=spacing)
    dt_pred = ndimage.distance_transform_edt(~pred, sampling=spacing)
    return dt_gt[_surface(pred)], dt_pred[_surface(gt)]


def asd(pred: np.ndarray, gt: np.ndarray, spacing=(1.0, 1.0, 1.0)) -> float:
    """Average symmetric surface distance : moyenne de toutes les distances de surface."""
    d1, d2 = surface_distances(pred, gt, spacing)
    return float(np.concatenate([d1, d2]).mean())


def mhd(pred: np.ndarray, gt: np.ndarray, spacing=(1.0, 1.0, 1.0), mode: str = "p95") -> float:
    d1, d2 = surface_distances(pred, gt, spacing)
    if mode == "p95":
        return float(np.percentile(np.concatenate([d1, d2]), 95))
    if mode == "dubuisson":
        return float(max(d1.mean(), d2.mean()))
    if mode == "max":
        return float(max(d1.max(), d2.max()))
    raise ValueError(mode)


def hausdorff(pred: np.ndarray, gt: np.ndarray, spacing=(1.0, 1.0, 1.0)) -> float:
    return mhd(pred, gt, spacing, mode="max")


def evaluate_subject(
    pred: np.ndarray,
    gt: np.ndarray,
    spacing=(1.0, 1.0, 1.0),
    classes: Iterable[int] = TISSUE_CLASSES,
    with_distances: bool = True,
) -> dict[str, float]:
    """Dictionnaire {dice_csf, dice_gm, dice_wm, asd_*, mhd_*, dice_mean} pour UN sujet.

    pred et gt : volumes de labels uint8 (0..3). Le fond n'est pas évalué.
    """
    out: dict[str, float] = {}
    for c in classes:
        name = CLASS_NAMES[c]
        p, g = pred == c, gt == c
        out[f"dice_{name}"] = dice(p, g)
        if with_distances:
            out[f"asd_{name}"] = asd(p, g, spacing)
            out[f"mhd_{name}"] = mhd(p, g, spacing)
    out["dice_mean"] = float(np.mean([out[f"dice_{CLASS_NAMES[c]}"] for c in classes]))
    return out
