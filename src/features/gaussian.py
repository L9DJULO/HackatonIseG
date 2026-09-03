"""BLOC B — descripteurs dérivés de gaussienne multi-échelle. 0 paramètre appris.

Pour chaque modalité (T1, T2 z-scorés dans le masque, 0 hors masque) et chaque sigma en mm
(converti en voxels par axe via le spacing) :
  smooth      : G_sigma * I
  gradmag     : sigma * ||grad(G_sigma * I)||               (normalisation d'échelle, ordre 1)
  lap         : sigma^2 * trace(Hessienne)                  (ordre 2)
  hess_e1..e3 : sigma^2 * valeurs propres de la Hessienne 3x3, TRIÉES par |lambda| croissante
                (invariance par rotation ; formule analytique vectorisée, pas de eigvalsh).
  dog_a_b     : smooth(sigma_b) - smooth(sigma_a) pour sigmas consécutifs.

Choix fixés a priori (à lister dans le rapport) : sigmas_mm, truncate=4.0, zéro hors masque.
Le calcul se fait sur la boîte englobante du masque élargie de 4*sigma_max voxels (identique
au calcul plein volume, juste plus rapide).
"""
from __future__ import annotations

import numpy as np
from scipy import ndimage

from src.features.base import FeatureExtractor
from src.features.intensity import zscore_in_mask
from src.io import Subject


def mask_bbox(mask: np.ndarray, margin: int) -> tuple[slice, ...]:
    sl = []
    for axis in range(mask.ndim):
        proj = np.any(mask, axis=tuple(i for i in range(mask.ndim) if i != axis))
        nz = np.flatnonzero(proj)
        sl.append(slice(max(nz[0] - margin, 0), min(nz[-1] + margin + 1, mask.shape[axis])))
    return tuple(sl)


def sym3x3_eigvals_sorted_abs(a11, a22, a33, a12, a13, a23) -> np.ndarray:
    """Valeurs propres de N matrices symétriques 3x3 (vecteurs de taille N), triées par |lambda|.

    Formule trigonométrique (Smith 1961), entièrement vectorisée. Retourne (N, 3).
    """
    a11, a22, a33, a12, a13, a23 = (np.asarray(x, dtype=np.float64) for x in (a11, a22, a33, a12, a13, a23))
    p1 = a12**2 + a13**2 + a23**2
    q = (a11 + a22 + a33) / 3.0
    p2 = (a11 - q) ** 2 + (a22 - q) ** 2 + (a33 - q) ** 2 + 2.0 * p1
    p = np.sqrt(p2 / 6.0)
    safe_p = np.where(p > 0, p, 1.0)
    b11, b22, b33 = (a11 - q) / safe_p, (a22 - q) / safe_p, (a33 - q) / safe_p
    b12, b13, b23 = a12 / safe_p, a13 / safe_p, a23 / safe_p
    det_b = b11 * (b22 * b33 - b23**2) - b12 * (b12 * b33 - b23 * b13) + b13 * (b12 * b23 - b22 * b13)
    r = np.clip(det_b / 2.0, -1.0, 1.0)
    phi = np.arccos(r) / 3.0
    e1 = q + 2.0 * p * np.cos(phi)
    e3 = q + 2.0 * p * np.cos(phi + 2.0 * np.pi / 3.0)
    e2 = 3.0 * q - e1 - e3
    eig = np.stack([e1, e2, e3], axis=1)
    eig = np.where((p > 0)[:, None], eig, np.repeat(q[:, None], 3, axis=1))
    order = np.argsort(np.abs(eig), axis=1, kind="stable")
    return np.take_along_axis(eig, order, axis=1)


class GaussianFeatures(FeatureExtractor):
    name = "gaussian"

    def __init__(self, sigmas_mm=(0.5, 1.0, 2.0, 4.0, 8.0), truncate: float = 4.0, modalities=("t1", "t2")):
        self.sigmas_mm = tuple(float(s) for s in sigmas_mm)
        self.truncate = float(truncate)
        self.modalities = tuple(modalities)

    @property
    def config(self) -> dict:
        return {"sigmas_mm": list(self.sigmas_mm), "truncate": self.truncate, "modalities": list(self.modalities)}

    @property
    def names(self) -> list[str]:
        out = []
        for mod in self.modalities:
            for s in self.sigmas_mm:
                out += [f"{mod}_s{s:g}_{k}" for k in ("smooth", "gradmag", "lap", "hess_e1", "hess_e2", "hess_e3")]
            for a, b in zip(self.sigmas_mm[:-1], self.sigmas_mm[1:]):
                out.append(f"{mod}_dog_{a:g}_{b:g}")
        return out

    def _scale_features(self, vol: np.ndarray, sel: np.ndarray, sigma_vox: tuple[float, ...], sigma_mm: float) -> list[np.ndarray]:
        gf = lambda order: ndimage.gaussian_filter(vol, sigma_vox, order=order, truncate=self.truncate, mode="constant")[sel]
        smooth = gf((0, 0, 0))
        d = [gf(tuple(1 if i == ax else 0 for i in range(3))) for ax in range(3)]
        gradmag = sigma_mm * np.sqrt(d[0] ** 2 + d[1] ** 2 + d[2] ** 2)
        h = {}
        for i in range(3):
            for j in range(i, 3):
                order = [0, 0, 0]
                order[i] += 1
                order[j] += 1
                h[(i, j)] = gf(tuple(order))
        lap = sigma_mm**2 * (h[(0, 0)] + h[(1, 1)] + h[(2, 2)])
        eig = sigma_mm**2 * sym3x3_eigvals_sorted_abs(h[(0, 0)], h[(1, 1)], h[(2, 2)], h[(0, 1)], h[(0, 2)], h[(1, 2)])
        return [smooth, gradmag, lap, eig[:, 0], eig[:, 1], eig[:, 2]]

    def transform(self, subject: Subject) -> np.ndarray:
        spacing = np.asarray(subject.spacing, dtype=np.float64)
        margin = int(np.ceil(self.truncate * max(self.sigmas_mm) / spacing.min()))
        crop = mask_bbox(subject.mask, margin)
        mask_c = subject.mask[crop]
        sel = mask_c  # les valeurs sont lues dans l'ordre C du crop == ordre de flatnonzero(mask)
        cols: list[np.ndarray] = []
        for mod in self.modalities:
            vol = zscore_in_mask(getattr(subject, mod), subject.mask)[crop].astype(np.float32)
            smooths = []
            for s in self.sigmas_mm:
                feats = self._scale_features(vol, sel, tuple(s / spacing), s)
                smooths.append(feats[0])
                cols += feats
            cols += [b - a for a, b in zip(smooths[:-1], smooths[1:])]
        X = np.stack(cols, axis=1).astype(np.float32)
        return self._check(subject, X)


BLOCKS = (GaussianFeatures,)
