"""Classifieurs de référence en attendant la famille de modèles définitive.

Les features arrivent DÉJÀ standardisées par sujet (src/features/normalize.py), donc aucun
modèle ici n'embarque de scaler ajusté sur le train. Le comptage des paramètres suit la
convention documentée dans src/models/params.py.
"""
from __future__ import annotations

import numpy as np
from sklearn.linear_model import LogisticRegression

N_CLASSES = 3


class RandomStub:
    """Prédit au hasard. Sert uniquement à valider la plomberie de bout en bout."""

    def __init__(self, seed: int = 0):
        self.rng = np.random.default_rng(seed)

    def fit(self, X: np.ndarray, y: np.ndarray) -> "RandomStub":
        return self

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        p = self.rng.random((X.shape[0], N_CLASSES)).astype(np.float32)
        return p / p.sum(axis=1, keepdims=True)

    def n_params(self) -> int:
        return 0

    def param_breakdown(self) -> dict[str, int]:
        return {}


class LogRegStub:
    """Régression logistique multinomiale, forme redondante de sklearn : 3 x (F + 1) poids."""

    def __init__(self, C: float = 1.0, max_iter: int = 300, seed: int = 0):
        self.C, self.max_iter, self.seed = C, max_iter, seed
        self.clf = LogisticRegression(C=C, max_iter=max_iter, random_state=seed)

    def fit(self, X: np.ndarray, y: np.ndarray) -> "LogRegStub":
        self.clf.fit(X, y)
        return self

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        p = self.clf.predict_proba(X).astype(np.float32)
        # sklearn ordonne les colonnes par classes_ triées ; on garantit l'ordre 1, 2, 3
        return p[:, np.argsort(self.clf.classes_)]

    def param_breakdown(self) -> dict[str, int]:
        return {"weights": int(self.clf.coef_.size), "bias": int(self.clf.intercept_.size)}

    def n_params(self) -> int:
        return sum(self.param_breakdown().values())


def build_stub(name: str, config: dict, seed: int):
    if name == "random":
        return RandomStub(seed=seed)
    if name == "logreg":
        return LogRegStub(seed=seed, **config)
    raise KeyError(name)
