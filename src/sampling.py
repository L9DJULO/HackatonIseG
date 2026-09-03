"""Échantillonnage équilibré des voxels d'entraînement + correction des priors.

POINT SUBTIL (à la frontière Jules/Arthur) : si le classifieur est entraîné sur une
distribution rééquilibrée (1/3 par tissu) alors que la vraie distribution est environ
CSF 22 % / GM 47 % / WM 31 %, ses probabilités sont biaisées. Correction à l'inférence :
    logit_corrigé_c = logit_c + log(prior_réel_c / prior_échantillon_c)
soit, sur les probabilités : p_c ∝ p_c * prior_réel_c / prior_échantillon_c.
Le prior "réel" est estimé sur les sujets d'ENTRAÎNEMENT du fold uniquement (pas de fuite).
Voir `adjust_priors`.
"""
from __future__ import annotations

import numpy as np
from scipy import ndimage

from src.io import TISSUE_CLASSES, Subject


def boundary_mask(label: np.ndarray, mask: np.ndarray) -> np.ndarray:
    """Voxels du masque dont le voisinage 6-connexe (dans le masque) contient >= 2 classes."""
    out = np.zeros(label.shape, dtype=bool)
    for axis in range(label.ndim):
        for shift in (1, -1):
            nb = np.roll(label, shift, axis=axis)
            nb_mask = np.roll(mask, shift, axis=axis)
            out |= mask & nb_mask & (nb != label)
    return out


def class_priors(subjects: list[Subject]) -> np.ndarray:
    """Proportion moyenne (par sujet, puis moyennée) des 3 tissus dans le masque."""
    props = []
    for s in subjects:
        y = s.mask_labels
        props.append([np.mean(y == c) for c in TISSUE_CLASSES])
    return np.mean(np.asarray(props, dtype=np.float64), axis=0)


def sample_voxels(
    subject: Subject,
    n_per_class: int,
    rng: np.random.Generator,
    boundary_frac: float = 0.0,
) -> tuple[np.ndarray, np.ndarray]:
    """Retourne (indices_dans_le_masque, labels) équilibrés entre les 3 tissus.

    indices_dans_le_masque indexe les lignes de FeatureExtractor.transform (ordre
    np.flatnonzero(mask)). Si boundary_frac > 0, AU MOINS cette fraction de chaque classe est
    tirée parmi les voxels de frontière (voisinage 6-connexe multi-classes) ; le reste est tiré
    uniformément sur toute la classe (frontière comprise). boundary_frac = 0 -> tirage uniforme.
    Tirage sans remise quand c'est possible, avec remise sinon.
    """
    if subject.label is None:
        raise ValueError("échantillonnage impossible sans label")
    y = subject.mask_labels
    is_boundary = getattr(subject, "_boundary_cache", None)
    if is_boundary is None:
        is_boundary = boundary_mask(subject.label, subject.mask).reshape(-1)[subject.mask_indices]
        subject._boundary_cache = is_boundary  # calculé une fois par sujet, réutilisé sur les 9 folds

    def draw(pool: np.ndarray, n: int) -> np.ndarray:
        if n <= 0 or pool.size == 0:
            return np.empty(0, dtype=np.int64)
        return rng.choice(pool, size=n, replace=pool.size < n)

    idx_parts, lab_parts = [], []
    for c in TISSUE_CLASSES:
        cls = np.flatnonzero(y == c)
        n_bnd = int(round(n_per_class * boundary_frac))
        bnd = draw(cls[is_boundary[cls]], n_bnd)
        rest = draw(cls, n_per_class - bnd.size)
        chosen = np.concatenate([bnd, rest])
        idx_parts.append(chosen)
        lab_parts.append(np.full(chosen.size, c, dtype=np.uint8))
    idx = np.concatenate(idx_parts)
    lab = np.concatenate(lab_parts)
    perm = rng.permutation(idx.size)
    return idx[perm], lab[perm]


def adjust_priors(proba: np.ndarray, sampled_prior: np.ndarray, target_prior: np.ndarray) -> np.ndarray:
    """Réajuste des probabilités apprises sous sampled_prior vers target_prior (Bayes)."""
    w = (np.asarray(target_prior, dtype=np.float64) / np.asarray(sampled_prior, dtype=np.float64))
    p = proba.astype(np.float64) * w[None, :]
    p /= p.sum(axis=1, keepdims=True)
    return p.astype(np.float32)
