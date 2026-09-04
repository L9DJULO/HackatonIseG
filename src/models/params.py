"""Convention de comptage des paramètres, écrite noir sur blanc pour être contestable.

Le critère du jury porte sur le Dice rapporté au nombre de paramètres. Le dénominateur doit
donc être vérifiable, et la frontière entre « paramètre appris » et « opération » doit être
explicite, y compris là où elle est discutable.

RÈGLE : est un paramètre appris toute quantité AJUSTÉE SUR LES SUJETS D'ENTRAÎNEMENT et
RÉUTILISÉE TELLE QUELLE à l'inférence. Autrement dit, toute quantité qui mémorise quelque
chose du jeu d'entraînement et qu'il faudrait sérialiser pour segmenter un nouveau sujet.

CE QUI COMPTE
  - les poids et les biais du classifieur, sans exception ;
  - toute statistique de normalisation estimée sur le train et figée pour l'inférence ;
  - pour un modèle à base d'arbres, deux valeurs par nœud de décision (seuil et indice de
    feature) plus une valeur par feuille ;
  - tout seuil ou pondération de post-traitement qui serait calibré sur les labels.

CE QUI NE COMPTE PAS
  - les statistiques recalculées sur le sujet courant à l'inférence : z-score intra-masque,
    médiane intra-masque, rang percentile, moyenne et écart-type par colonne calculés sur le
    masque du sujet segmenté (src/features/normalize.py). Elles ne mémorisent rien du train :
    segmenter un nouveau sujet ne demande de transporter aucune de ces valeurs. C'est le même
    statut qu'un filtre gaussien ou qu'un calcul d'aire.
  - les hyperparamètres fixés a priori : sigmas des gaussiennes, seuils d'aire de l'arbre des
    formes, nombre de niveaux de quantification, rayons de voisinage. Ils ne sont pas ajustés
    sur les données, mais ils sont listés avec leurs valeurs dans le docstring de chaque bloc
    et recopiés dans chaque JSON de résultats sous `feature_config`.
  - la structure des features elle-même (aucun extracteur n'a de paramètre appris, ce que
    `FeatureExtractor.n_learned_params` affirme et que les tests vérifient).

ZONE GRISE ASSUMÉE. La standardisation par sujet est le point contestable : un jury peut
considérer que le simple fait de standardiser est une décision informée par les données.
Nous répondons que la transformation est identique à l'entraînement et à l'inférence, qu'elle
n'utilise que le sujet courant, et qu'aucune valeur issue du train n'est transportée. Le choix
inverse est chiffrable : il ajouterait 2 x n_features au décompte, soit 302 paramètres pour la
configuration finale à 151 features. Les deux chiffres sont donnés dans le rapport.

CONVENTION SKLEARN. On compte la forme REDONDANTE de sklearn, 3 x (F + 1) pour trois classes,
et non la paramétrisation minimale 2 x (F + 1). C'est le nombre de valeurs réellement stockées
dans `coef_` et `intercept_`. C'est la convention la moins avantageuse pour nous : on ne veut
pas d'un décompte qui flatte le résultat.
"""
from __future__ import annotations

import numpy as np


def count_linear(n_features: int, n_classes: int = 3, redundant: bool = True) -> int:
    """Nombre de poids d'un modèle linéaire multinomial, biais compris."""
    rows = n_classes if redundant else n_classes - 1
    return rows * (n_features + 1)


def count_mlp(n_features: int, hidden: list[int], n_classes: int = 3) -> int:
    """Somme des poids et des biais de chaque couche."""
    sizes = [n_features, *hidden, n_classes]
    return sum(a * b + b for a, b in zip(sizes[:-1], sizes[1:]))


def count_sklearn(model) -> int:
    """Décompte automatique depuis les attributs ajustés de sklearn."""
    total = 0
    for attr in ("coef_", "intercept_", "coefs_", "intercepts_"):
        value = getattr(model, attr, None)
        if value is None:
            continue
        parts = value if isinstance(value, list) else [value]
        total += sum(int(np.asarray(p).size) for p in parts)
    return total


def check_agreement(declared: int, model, tolerance: int = 0) -> None:
    """Lève une erreur si le décompte déclaré s'écarte du décompte automatique."""
    automatic = count_sklearn(model)
    if abs(declared - automatic) > tolerance:
        raise ValueError(
            f"comptage incohérent : déclaré {declared}, calculé depuis le modèle {automatic}. "
            "Le dénominateur du critère doit être vérifiable."
        )
