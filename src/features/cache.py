"""Cache disque des features : un .npy par (sujet, bloc, config), lu en memmap.

Les blocs ne sont JAMAIS recalculés pendant l'entraînement. `cache/` est ignoré par git.
La clé de cache inclut la config du bloc : changer un sigma invalide le cache automatiquement.
"""
from __future__ import annotations

import json
import os
import time
from pathlib import Path

import numpy as np

from src.features.base import FeatureExtractor
from src.io import Subject


class CachedExtractor(FeatureExtractor):
    def __init__(self, block: FeatureExtractor, cache_dir: Path, verbose: bool = True):
        self.block = block
        self.cache_dir = Path(cache_dir)
        self.verbose = verbose

    @property
    def name(self) -> str:  # type: ignore[override]
        return self.block.name

    @property
    def names(self) -> list[str]:
        return self.block.names

    @property
    def config(self) -> dict:
        return self.block.config

    @property
    def cache_key(self) -> str:
        return self.block.cache_key

    def path(self, subject_id: int) -> Path:
        return self.cache_dir / f"subject-{subject_id}" / f"{self.block.cache_key}.npy"

    def transform(self, subject: Subject) -> np.ndarray:
        p = self.path(subject.subject_id)
        if p.exists():
            X = np.load(p, mmap_mode="r")
            if X.shape == (int(subject.mask.sum()), self.n_features):
                return X
        t0 = time.time()
        X = self.block.transform(subject)
        p.parent.mkdir(parents=True, exist_ok=True)
        tmp = p.with_name(f"{p.stem}.tmp{os.getpid()}.npy")
        np.save(tmp, X)
        tmp.replace(p)
        p.with_suffix(".json").write_text(json.dumps({"names": self.names, "config": self.config}, indent=1))
        if self.verbose:
            print(f"  [cache] {self.block.name} subject-{subject.subject_id}: {X.shape} en {time.time() - t0:.1f}s")
        return np.load(p, mmap_mode="r")
