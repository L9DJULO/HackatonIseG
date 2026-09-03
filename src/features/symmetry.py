"""BLOC E — symétrie hémisphérique. 0 paramètre appris.

Le cerveau est quasi symétrique par rapport au plan sagittal médian : les tissus d'un voxel
et de son miroir sont le plus souvent identiques, et une asymétrie d'intensité locale signale
une frontière ou une structure impaire (ventricules, sillon interhémisphérique = LCR).
Le plan est celui du bloc spatial (PCA, axe le plus aligné avec l'axe image gauche-droite).
Pour chaque modalité z-scorée dans le masque : valeur au point miroir (interpolation
trilinéaire, 0 hors masque) et différence voxel - miroir.
"""
from __future__ import annotations

import numpy as np
from scipy import ndimage

from src.features.base import FeatureExtractor
from src.features.intensity import zscore_in_mask
from src.features.spatial import principal_axes
from src.io import Subject


def mirror_coordinates(subject: Subject) -> np.ndarray:
    """Coordonnées (voxels, 3 x n) des points miroirs des voxels du masque."""
    spacing = np.asarray(subject.spacing, dtype=np.float64)
    idx = np.stack(np.nonzero(subject.mask), axis=1).astype(np.float64)
    coords = idx * spacing
    c, axes = principal_axes(coords)
    n = axes[:, 0]  # normale du plan sagittal médian
    d = (coords - c) @ n
    mirrored = coords - 2.0 * d[:, None] * n[None, :]
    return (mirrored / spacing).T


class SymmetryFeatures(FeatureExtractor):
    name = "symmetry"

    def __init__(self, modalities=("t1", "t2")):
        self.modalities = tuple(modalities)

    @property
    def config(self) -> dict:
        return {"modalities": list(self.modalities), "interpolation": "trilinear", "plane": "pca_spatial"}

    @property
    def names(self) -> list[str]:
        return [f"{m}_{k}" for m in self.modalities for k in ("mirror", "mirror_diff")]

    def transform(self, subject: Subject) -> np.ndarray:
        mc = mirror_coordinates(subject)
        cols = []
        for mod in self.modalities:
            z = zscore_in_mask(getattr(subject, mod), subject.mask)
            here = z[subject.mask]
            mirror = ndimage.map_coordinates(z, mc, order=1, mode="constant", cval=0.0)
            cols += [mirror, here - mirror]
        return self._check(subject, np.stack(cols, axis=1).astype(np.float32))


BLOCKS = (SymmetryFeatures,)
