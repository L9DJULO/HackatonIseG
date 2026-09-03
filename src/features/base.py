"""Interface FeatureExtractor (contrat commun, ne pas modifier unilatéralement)."""
from __future__ import annotations

import hashlib
import json

import numpy as np

from src.io import Subject


class FeatureExtractor:
    """Tous nos extracteurs ont n_learned_params == 0 : rien n'est ajusté sur les données.

    Hyperparamètres fixés a priori (sigmas, seuils...) : exposés via `config` pour être
    listés dans le rapport et pour la clé de cache.
    """

    name: str = "base"

    @property
    def names(self) -> list[str]:
        raise NotImplementedError

    @property
    def n_features(self) -> int:
        return len(self.names)

    @property
    def n_learned_params(self) -> int:
        return 0

    @property
    def config(self) -> dict:
        """Hyperparamètres fixes de l'extracteur (sérialisables JSON)."""
        return {}

    @property
    def cache_key(self) -> str:
        payload = json.dumps({"name": self.name, "config": self.config, "names": self.names}, sort_keys=True)
        return f"{self.name}-{hashlib.sha1(payload.encode()).hexdigest()[:8]}"

    def transform(self, subject: Subject) -> np.ndarray:
        """(n_voxels_dans_le_masque, n_features) float32, ordre = np.flatnonzero(subject.mask)."""
        raise NotImplementedError

    def _check(self, subject: Subject, X: np.ndarray) -> np.ndarray:
        n = int(subject.mask.sum())
        if X.shape != (n, self.n_features):
            raise RuntimeError(f"{self.name}: shape {X.shape} attendue ({n}, {self.n_features})")
        if not np.isfinite(X).all():
            raise RuntimeError(f"{self.name}: valeurs non finies")
        return X.astype(np.float32, copy=False)
