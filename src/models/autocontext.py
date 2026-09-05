"""Auto-contexte [@tu2010autocontext] à deux étages, avec sa validation croisée interne.

L'IDÉE. Le classifieur décide voxel par voxel. Le bloc `context` des features lui donne déjà
un voisinage, mais sur les INTENSITÉS. L'auto-contexte lui donne un voisinage sur les
DÉCISIONS : un premier étage produit une carte de probabilités, on en extrait des colonnes de
voisinage, et un second étage lit les features d'origine ET ces colonnes. Un voxel isolément
ambigu devient décidable si tout ce qui l'entoure penche déjà d'un côté — exactement ce qui
manque en phase isointense, où l'intensité locale ne sépare pas.

LE PIÈGE, ET LA VALIDATION CROISÉE INTERNE. Si l'on entraîne le second étage sur des cartes
de probabilités que le premier a produites SUR SES PROPRES DONNÉES D'ENTRAÎNEMENT, ces cartes
sont anormalement bonnes : le premier étage a déjà vu ces voxels. Le second étage apprend
alors à faire une confiance excessive au premier, et l'ensemble s'effondre à l'inférence, où
les cartes sont de qualité ordinaire. La parade est un K-fold INTERNE aux sujets
d'entraînement du pli courant : les colonnes de contexte d'un sujet sont toujours produites
par un modèle qui n'a jamais vu ce sujet. C'est la seule façon d'avoir un second étage
calibré sur la qualité réelle du premier.

Aucune fuite vers le sujet de test : le K-fold interne ne partitionne que les neuf sujets
d'entraînement du pli, et le sujet laissé dehors par la boucle externe n'entre nulle part.

COMPTAGE DES PARAMÈTRES. Sont transportés à l'inférence, donc comptés (src/models/params.py) :
les poids du premier étage FINAL (réentraîné sur les neuf sujets) et ceux du second étage. Les
modèles des plis internes sont jetés après avoir servi à fabriquer les colonnes de contexte :
ils ne sont pas transportés et ne comptent pas. Le lissage qui produit les colonnes de contexte
est une convolution à sigma fixé a priori, sans rien de mémorisé.
"""
from __future__ import annotations

import numpy as np
from scipy import ndimage

from src.io import Subject, mask_to_volume

N_CLASSES = 3
CONTEXT_SIGMAS_MM = (1.0, 2.0, 4.0)
"""Rayons du voisinage de décision, en millimètres, fixés a priori. Trois échelles : le voxel
et son entourage immédiat, le pli, et la structure. Aucune n'est ajustée sur les données."""

EPS = 1e-8


def context_columns(proba_rows: np.ndarray, subject: Subject) -> np.ndarray:
    """Colonnes de contexte lues sur une carte de probabilités.

    Pour chaque classe et chaque sigma, la probabilité moyenne dans le voisinage gaussien, en
    convolution normalisée par le masque pour ne pas diluer le bord. Rend
    (n_voxels_du_masque, 3 * len(CONTEXT_SIGMAS_MM)), dans l'ordre canonique du masque.
    """
    vol = mask_to_volume(np.asarray(proba_rows, dtype=np.float32), subject.mask)
    m = subject.mask.astype(np.float32)
    idx = subject.mask_indices
    out = []
    for sigma_mm in CONTEXT_SIGMAS_MM:
        sigma = tuple(sigma_mm / float(s) for s in subject.spacing)
        weight = ndimage.gaussian_filter(m, sigma=sigma, mode="constant")
        for c in range(N_CLASSES):
            num = ndimage.gaussian_filter(vol[..., c] * m, sigma=sigma, mode="constant")
            out.append((num / np.maximum(weight, EPS)).reshape(-1)[idx])
    return np.stack(out, axis=1).astype(np.float32)


def n_context_columns() -> int:
    return N_CLASSES * len(CONTEXT_SIGMAS_MM)


def context_column_names() -> list[str]:
    return [f"autocontext/p{c + 1}_sigma{s:g}mm" for s in CONTEXT_SIGMAS_MM for c in range(N_CLASSES)]


class AutoContext:
    """Deux étages du même classifieur de base, reliés par des colonnes de contexte.

    `base_factory()` doit rendre un classifieur neuf exposant fit / predict_proba / n_params /
    param_breakdown, exactement comme les modèles de src/models/stub.py.
    """

    needs_context = True

    def __init__(self, base_factory, n_inner_folds: int = 3, seed: int = 0):
        if n_inner_folds < 2:
            raise ValueError("le K-fold interne demande au moins 2 plis")
        self.base_factory = base_factory
        self.n_inner_folds = n_inner_folds
        self.seed = seed
        self.stage1 = None
        self.stage2 = None

    # -- entraînement ----------------------------------------------------------------------

    def fit(self, X: np.ndarray, y: np.ndarray, context=None) -> "AutoContext":
        if context is None:
            raise RuntimeError(
                "AutoContext exige le contexte spatial des sujets d'entraînement ; "
                "la boucle LOO le fournit quand model.needs_context est vrai"
            )
        subjects = list(context.subjects)
        if len(subjects) < self.n_inner_folds:
            raise ValueError(f"{len(subjects)} sujets pour {self.n_inner_folds} plis internes")

        # 1. K-fold interne : les colonnes de contexte d'un sujet viennent d'un modèle
        #    qui ne l'a jamais vu.
        order = sorted(subjects, key=lambda s: s.subject_id)
        folds = [order[i :: self.n_inner_folds] for i in range(self.n_inner_folds)]
        ctx_by_subject: dict[int, np.ndarray] = {}
        for held_out in folds:
            held_ids = {s.subject_id for s in held_out}
            keep = np.concatenate([context.rows_mask(s.subject_id) for s in order if s.subject_id not in held_ids])
            inner = self.base_factory()
            inner.fit(X[keep], y[keep])
            for s in held_out:
                proba = inner.predict_proba(context.features(s))
                ctx_by_subject[s.subject_id] = context_columns(proba, s)

        # 2. second étage : features d'origine + colonnes de contexte, sur les mêmes voxels
        #    échantillonnés que le premier étage.
        ctx_rows = np.concatenate(
            [ctx_by_subject[s.subject_id][context.sampled_rows(s.subject_id)] for s in order]
        )
        order_rows = np.concatenate([context.rows_mask(s.subject_id) for s in order])
        ctx_full = np.empty((X.shape[0], n_context_columns()), dtype=np.float32)
        ctx_full[order_rows] = ctx_rows
        X2 = np.concatenate([np.asarray(X, dtype=np.float32), ctx_full], axis=1)

        # 3. premier étage FINAL, celui qui sera transporté : réentraîné sur les neuf sujets.
        self.stage1 = self.base_factory()
        self.stage1.fit(X, y)
        self.stage2 = self.base_factory()
        self.stage2.fit(X2, y)
        return self

    # -- inférence -------------------------------------------------------------------------

    def predict_proba_subject(self, X_full: np.ndarray, subject: Subject) -> np.ndarray:
        """Chaîne complète sur un sujet entier : étage 1, contexte, étage 2."""
        p1 = self.stage1.predict_proba(X_full)
        ctx = context_columns(p1, subject)
        X2 = np.concatenate([np.asarray(X_full, dtype=np.float32), ctx], axis=1)
        return self.stage2.predict_proba(X2).astype(np.float32)

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        raise RuntimeError(
            "AutoContext ne peut pas prédire sur des lignes détachées de leur volume : "
            "utiliser predict_proba_subject(X_full, subject)"
        )

    # -- comptage --------------------------------------------------------------------------

    def param_breakdown(self) -> dict[str, int]:
        out = {f"stage1_{k}": v for k, v in self.stage1.param_breakdown().items()}
        out.update({f"stage2_{k}": v for k, v in self.stage2.param_breakdown().items()})
        return out

    def n_params(self) -> int:
        """Étages 1 et 2 seulement : les modèles des plis internes ne sont pas transportés."""
        return int(self.stage1.n_params() + self.stage2.n_params())
