"""Stubs de classifieurs en attendant les vrais modèles (src/models/*).

Deux classifieurs respectant l'interface VoxelClassifier du contrat :
- RandomStub : prédit au hasard, sert uniquement à tester la plomberie.
- LogRegStub : régression logistique sklearn, sert aux runs d'ablation bloc par bloc.
  Convention de comptage (forme redondante de sklearn, 3 classes) :
  n_params = coef_.size + intercept_.size = (n_features + 1) * 3.
  La convention définitive sera fixée dans params.py ; celle-ci est surestimée
  d'un facteur 3/2 par rapport à la paramétrisation minimale (n_features + 1) * 2.
"""
from __future__ import annotations

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler

N_CLASSES = 3


class RandomStub:
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
    """Logistic regression multinomiale avec standardisation des features.

    Le StandardScaler ajuste 2 * n_features statistiques sur le train : ce ne sont pas des
    poids de décision mais on les compte quand même dans param_breakdown sous "scaler"
    pour être irréprochable (convention finale à fixer dans params.py).
    """

    def __init__(self, C: float = 1.0, max_iter: int = 300, seed: int = 0, count_scaler: bool = True):
        self.C, self.max_iter, self.seed, self.count_scaler = C, max_iter, seed, count_scaler
        self.scaler = StandardScaler()
        self.clf = LogisticRegression(C=C, max_iter=max_iter, random_state=seed)

    def fit(self, X: np.ndarray, y: np.ndarray) -> "LogRegStub":
        self.clf.fit(self.scaler.fit_transform(X), y)
        return self

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        p = self.clf.predict_proba(self.scaler.transform(X)).astype(np.float32)
        # sklearn ordonne les colonnes par classes_ triées ; on garantit l'ordre 1,2,3
        order = np.argsort(self.clf.classes_)
        return p[:, order]

    def param_breakdown(self) -> dict[str, int]:
        d = {"weights": int(self.clf.coef_.size), "bias": int(self.clf.intercept_.size)}
        if self.count_scaler:
            d["scaler"] = int(2 * self.scaler.mean_.size)
        return d

    def n_params(self) -> int:
        return sum(self.param_breakdown().values())


def build_stub(name: str, config: dict, seed: int):
    if name == "random":
        return RandomStub(seed=seed)
    if name == "logreg":
        return LogRegStub(seed=seed, **config)
    raise KeyError(name)
