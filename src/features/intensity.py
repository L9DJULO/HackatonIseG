"""BLOC A — intensités. 0 paramètre appris. Toutes les statistiques sont PAR SUJET, dans le masque.

LEÇON APPRISE (fold subject-7) : le gain d'acquisition varie d'un sujet à l'autre par
modalité. Un ratio sur intensités brutes est donc décalé d'un sujet à l'autre (Dice GM = 0
sur le sujet 7). On normalise chaque modalité par sa MÉDIANE intra-masque avant le ratio,
ce qui le rend invariant à un facteur d'échelle par modalité.
"""
from __future__ import annotations

import numpy as np

from src.features.base import FeatureExtractor
from src.io import Subject


def zscore_in_mask(vol: np.ndarray, mask: np.ndarray) -> np.ndarray:
    """z-score calculé sur les voxels du masque uniquement ; 0 hors masque."""
    v = vol[mask].astype(np.float64)
    out = np.zeros(vol.shape, dtype=np.float32)
    out[mask] = (v - v.mean()) / (v.std() + 1e-6)
    return out


def percentile_rank(values: np.ndarray) -> np.ndarray:
    """Rang percentile dans [0, 1] de chaque valeur au sein de son propre vecteur."""
    order = np.argsort(values, kind="stable")
    ranks = np.empty(values.size, dtype=np.float32)
    ranks[order] = np.arange(values.size, dtype=np.float32)
    return ranks / max(values.size - 1, 1)


class IntensityFeatures(FeatureExtractor):
    name = "intensity"

    def __init__(self, eps: float = 1e-3):
        self.eps = eps

    @property
    def config(self) -> dict:
        return {"eps": self.eps, "ratio_normalisation": "median_in_mask"}

    @property
    def names(self) -> list[str]:
        return ["t1_z", "t2_z", "t1t2_ratio", "zdiff", "t1_pct", "t2_pct"]

    def transform(self, subject: Subject) -> np.ndarray:
        m = subject.mask
        t1 = subject.t1[m].astype(np.float64)
        t2 = subject.t2[m].astype(np.float64)
        t1_z = (t1 - t1.mean()) / (t1.std() + 1e-6)
        t2_z = (t2 - t2.mean()) / (t2.std() + 1e-6)
        t1_n = t1 / (np.median(t1) + 1e-6)
        t2_n = t2 / (np.median(t2) + 1e-6)
        ratio = (t1_n - t2_n) / (t1_n + t2_n + self.eps)
        X = np.stack([t1_z, t2_z, ratio, t1_z - t2_z, percentile_rank(t1), percentile_rank(t2)], axis=1)
        return self._check(subject, X.astype(np.float32))


BLOCKS = (IntensityFeatures,)
