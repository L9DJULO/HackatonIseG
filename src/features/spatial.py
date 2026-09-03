"""BLOC C — prior spatial gratuit. 0 paramètre appris. Tout est relatif au masque du sujet.

Features :
  x_norm, y_norm, z_norm : coordonnées normalisées dans [0, 1] par la boîte englobante du masque.
  x_abs                  : |x_norm - 0.5|, version symétrique gauche/droite (sans PCA).
  dist_border            : distance euclidienne (mm) au bord du masque / rayon maximal (max de la
                           transformée de distance) -> [0, 1]. Sépare le LCR périphérique.
  dist_midsag            : distance ABSOLUE au plan sagittal médian, normalisée par la demi-largeur
                           du masque. Plan estimé par PCA des coordonnées des voxels du masque :
                           on prend l'axe principal LE PLUS ALIGNÉ avec l'axe gauche-droite de
                           l'image (axe 0 : l'affine Analyze est diag(-1, 1, 1)), signe fixé
                           positif sur cet axe. La valeur absolue rend la feature symétrique
                           gauche/droite.
  r_norm                 : rayon sphérique depuis le centroïde / rayon max.
  cos_elev               : cosinus de l'angle entre (p - centroïde) et l'axe supérieur-inférieur
                           estimé (axe PCA le plus aligné avec l'axe image 2).
  azim_abs               : azimut dans le plan axial, mesuré depuis l'axe antéro-postérieur (axe
                           PCA aligné avec l'axe image 1), replié dans [0, pi] (symétrie G/D).
Hypothèse d'orientation VÉRIFIÉE sur les headers : axes image = (G-D, A-P, S-I).
"""
from __future__ import annotations

import numpy as np
from scipy import ndimage

from src.features.base import FeatureExtractor
from src.io import Subject


def principal_axes(coords_mm: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Centroïde et axes PCA (colonnes de V), chaque axe ré-assigné à l'axe image le plus
    proche et orienté positivement le long de cet axe image (convention explicite)."""
    c = coords_mm.mean(axis=0)
    cov = np.cov((coords_mm - c).T)
    _, vecs = np.linalg.eigh(cov)
    axes = np.zeros((3, 3))
    taken = set()
    # assignation gloutonne : axe image i <- vecteur propre le plus aligné non encore pris
    for img_axis in range(3):
        best = max((j for j in range(3) if j not in taken), key=lambda j: abs(vecs[img_axis, j]))
        taken.add(best)
        v = vecs[:, best]
        axes[:, img_axis] = v if v[img_axis] >= 0 else -v
    return c, axes


class SpatialFeatures(FeatureExtractor):
    name = "spatial"

    @property
    def names(self) -> list[str]:
        return ["x_norm", "y_norm", "z_norm", "x_abs", "dist_border", "dist_midsag", "r_norm", "cos_elev", "azim_abs"]

    def transform(self, subject: Subject) -> np.ndarray:
        mask = subject.mask
        spacing = np.asarray(subject.spacing, dtype=np.float64)
        idx = np.stack(np.nonzero(mask), axis=1).astype(np.float64)  # ordre C == flatnonzero
        lo, hi = idx.min(axis=0), idx.max(axis=0)
        xyz_norm = (idx - lo) / np.maximum(hi - lo, 1)

        dt = ndimage.distance_transform_edt(mask, sampling=tuple(spacing))
        dist_border = dt[mask] / max(dt.max(), 1e-6)

        coords = idx * spacing
        c, axes = principal_axes(coords)
        rel = coords - c
        proj = rel @ axes  # colonnes : (G-D, A-P, S-I)
        half_width = max(np.abs(proj[:, 0]).max(), 1e-6)
        dist_midsag = np.abs(proj[:, 0]) / half_width
        r = np.linalg.norm(rel, axis=1)
        r_norm = r / max(r.max(), 1e-6)
        cos_elev = proj[:, 2] / np.maximum(r, 1e-6)
        azim_abs = np.abs(np.arctan2(proj[:, 0], proj[:, 1]))

        X = np.stack(
            [xyz_norm[:, 0], xyz_norm[:, 1], xyz_norm[:, 2], np.abs(xyz_norm[:, 0] - 0.5), dist_border, dist_midsag, r_norm, cos_elev, azim_abs],
            axis=1,
        ).astype(np.float32)
        return self._check(subject, X)


BLOCKS = (SpatialFeatures,)
