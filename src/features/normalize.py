"""Standardisation des features PAR SUJET, cohérente avec le reste du pipeline.

Doctrine : toute normalisation se calcule sur le sujet courant, dans son masque cérébral, à
l'entraînement comme à l'inférence. La moyenne et l'écart-type de chaque colonne sont donc
recalculés sur le sujet qu'on est en train de segmenter. Ils ne mémorisent rien du jeu
d'entraînement et ne comptent pas comme des paramètres appris (voir src/models/params.py).

Les statistiques sont calculées sur TOUS les voxels du masque du sujet, pas sur l'échantillon
d'entraînement, pour que la transformation soit rigoureusement la même dans les deux régimes.
Elles sont mises en cache sur disque, une entrée par sujet et par jeu de features.
"""
from __future__ import annotations

import hashlib
from pathlib import Path

import numpy as np

from src.io import Subject

EPS = 1e-6


def stats_key(feature_keys: list[str]) -> str:
    return hashlib.sha1("|".join(feature_keys).encode()).hexdigest()[:12]


def subject_stats(extractor, subject: Subject, cache_dir: Path | None = None, chunk: int = 200_000) -> tuple[np.ndarray, np.ndarray]:
    """(moyenne, écart-type) de chaque colonne sur les voxels du masque du sujet."""
    key = stats_key([b.cache_key for b in extractor.blocks])
    path = None
    if cache_dir is not None:
        path = Path(cache_dir) / f"subject-{subject.subject_id}" / f"stats-{key}.npz"
        if path.exists():
            d = np.load(path)
            if d["mean"].shape == (extractor.n_features,):
                return d["mean"], d["std"]
    X = extractor.transform(subject)
    n = X.shape[0]
    total = np.zeros(X.shape[1], dtype=np.float64)
    total_sq = np.zeros(X.shape[1], dtype=np.float64)
    for start in range(0, n, chunk):
        block = np.asarray(X[start : start + chunk], dtype=np.float64)
        total += block.sum(axis=0)
        total_sq += (block**2).sum(axis=0)
    mean = total / n
    std = np.sqrt(np.maximum(total_sq / n - mean**2, 0.0)) + EPS
    if path is not None:
        path.parent.mkdir(parents=True, exist_ok=True)
        np.savez(path, mean=mean, std=std)
    return mean, std


def apply_stats(X: np.ndarray, stats: tuple[np.ndarray, np.ndarray] | None) -> np.ndarray:
    if stats is None:
        return np.asarray(X, dtype=np.float32)
    mean, std = stats
    return ((np.asarray(X, dtype=np.float64) - mean) / std).astype(np.float32)
