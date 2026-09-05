"""Sélection de features : garder les K colonnes les plus utiles, et COMPTER ce que ça coûte.

Le point de méthode, qui n'est pas anodin dans un projet dont le critère est le nombre de
paramètres : la sélection N'EST PAS GRATUITE. Les indices des colonnes retenues sont ajustés
sur les sujets d'entraînement et doivent être transportés pour segmenter un nouveau sujet —
sans eux, on ne sait pas quelles colonnes donner au modèle. Ils tombent donc exactement sous
la règle de src/models/params.py et sont comptés, à raison d'un entier par colonne retenue.

Passer de F à K colonnes fait donc passer le décompte de 3(F+1) à 3(K+1) + K. La sélection
n'est rentable que si K est nettement inférieur à F : à F = 151, descendre à K = 40 fait
passer de 456 à 163 paramètres. Le rapport doit présenter le gain net, pas seulement la
réduction du nombre de poids.

Le critère est calculé SUR LES DONNÉES D'ENTRAÎNEMENT DU PLI uniquement, jamais sur le sujet
de test : la sélection est faite dans `fit`, qui ne reçoit que l'échantillon d'entraînement.
"""
from __future__ import annotations

import numpy as np


class SelectedFeatures:
    """Enveloppe un classifieur de base et ne lui montre que K colonnes.

    Critère : un premier ajustement du modèle de base sur toutes les colonnes, puis les K
    colonnes de plus grand poids absolu maximal sur les trois classes. C'est le critère le
    plus honnête à disposition ici — il mesure l'usage réel que le modèle fait d'une colonne,
    là où un critère univarié ignorerait les redondances entre colonnes.
    """

    def __init__(self, base_factory, k: int, seed: int = 0):
        if k < 1:
            raise ValueError("k doit valoir au moins 1")
        self.base_factory = base_factory
        self.k = k
        self.seed = seed
        self.support_: np.ndarray | None = None
        self.model = None

    def fit(self, X: np.ndarray, y: np.ndarray) -> "SelectedFeatures":
        X = np.asarray(X, dtype=np.float32)
        k = min(self.k, X.shape[1])
        probe = self.base_factory()
        probe.fit(X, y)
        score = self._importance(probe, X.shape[1])
        # tri décroissant, départage par indice croissant pour être déterministe
        self.support_ = np.sort(np.lexsort((np.arange(X.shape[1]), -score))[:k])
        self.model = self.base_factory()
        self.model.fit(X[:, self.support_], y)
        return self

    @staticmethod
    def _importance(probe, n_features: int) -> np.ndarray:
        coef = getattr(getattr(probe, "clf", None), "coef_", None)
        if coef is None:
            raise TypeError("le modèle de base n'expose pas de coefficients : critère indisponible")
        coef = np.asarray(coef)
        if coef.shape[1] != n_features:
            raise RuntimeError(f"coef_ a {coef.shape[1]} colonnes pour {n_features} features")
        return np.abs(coef).max(axis=0)

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        if self.support_ is None:
            raise RuntimeError("appeler fit avant predict_proba")
        return self.model.predict_proba(np.asarray(X, dtype=np.float32)[:, self.support_])

    def param_breakdown(self) -> dict[str, int]:
        out = dict(self.model.param_breakdown())
        out["feature_indices"] = int(self.support_.size)
        return out

    def n_params(self) -> int:
        return sum(self.param_breakdown().values())

    @property
    def selected_names(self) -> list[int]:
        return [] if self.support_ is None else self.support_.tolist()
