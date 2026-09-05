"""Post-traitement spatial et topologique, à ZÉRO paramètre appris.

Le classifieur décide voxel par voxel, sans jamais voir ses voisins. Trois défauts en
découlent, tous visibles à l'œil sur les cartes de sortie : du bruit poivre-et-sel dans les
régions homogènes, des composantes minuscules isolées, et des contacts directs entre
substance blanche et liquide céphalo-rachidien.

AVERTISSEMENT MESURÉ SUR LE TROISIÈME. L'étape `gm_between` part de l'idée que le ruban
cortical s'interpose partout entre substance blanche et LCR. C'est vrai en surface, et faux
aux ventricules : la substance blanche périventriculaire borde directement le LCR
ventriculaire, sans matière grise entre les deux. La contrainte est donc anatomiquement
fausse là où elle s'applique le plus souvent, et la mesure le confirme — voir
`report/assets/stats.md`, la configuration avec `gm_between` perd du Dice contre la
configuration sans post-traitement. NE PAS l'inclure dans une séquence de production sans
avoir d'abord restreint son application à la surface corticale. Elle est conservée ici parce
que le résultat négatif est documenté dans le rapport, et parce qu'une version restreinte au
LCR sous-arachnoïdien reste une piste défendable.

Ce module corrige les trois, et le fait sans rien mémoriser du jeu d'entraînement. C'est le
point qui compte pour la convention de comptage (src/models/params.py) : TOUS les seuils
ci-dessous sont fixés a priori, à partir de considérations anatomiques ou de l'échelle du
voxel, et aucun n'est calibré sur les labels. Un seuil ajusté sur les labels d'entraînement
serait un paramètre appris et devrait être compté ; ce n'est le cas d'aucun de ceux-ci, et
`n_learned_params()` renvoie 0 pour toute séquence d'étapes.

Étapes disponibles, à composer dans l'ordre voulu depuis le YAML :

  smooth            lissage gaussien des probabilités (sigma fixé, en millimètres), en
                    convolution normalisée pour ne pas diluer le bord du masque ;
  small_components  suppression des composantes connexes plus petites qu'un volume fixé ;
                    les voxels retirés repassent à leur meilleure classe suivante ;
  fill_wm_holes     bouchage des cavités entièrement incluses dans la substance blanche ;
  gm_between        contrainte topologique : aucun voxel de substance blanche ne peut être
                    6-adjacent à un voxel de LCR. Vraie au cortex, FAUSSE aux ventricules :
                    lire l'avertissement ci-dessus avant de l'utiliser.

Toutes opèrent sur le volume de probabilités (D, H, W, 3) et rendent un volume d'étiquettes
(D, H, W) uint8 dans {0, 1, 2, 3}, 0 hors masque.
"""
from __future__ import annotations

import numpy as np
from scipy import ndimage

from src.io import TISSUE_CLASSES

# --- Hyperparamètres FIXÉS A PRIORI. Aucun n'est ajusté sur les données. -------------------
SMOOTH_SIGMA_MM = 1.0
"""Écart-type du lissage, en millimètres. Choisi à l'échelle du voxel (1 mm isotrope) : il
régularise le bruit voxel à voxel sans déplacer une frontière tissulaire, dont le rayon de
courbure est très supérieur."""

MIN_COMPONENT_MM3 = 30.0
"""Volume minimal d'une composante connexe de tissu, en mm³. Trente millimètres cubes, soit
un cube de trois voxels de côté environ : en dessous, aucune structure des trois tissus n'est
anatomiquement plausible à cette résolution."""

MAX_GM_BETWEEN_PASSES = 8
"""Nombre de passes « à la marge », celles qui tranchent du côté le moins sûr. Deux ou trois
suffisent en pratique. Ce qui reste au-delà est résolu par la passe forcée décrite dans
enforce_gm_between : la contrainte est garantie, pas espérée."""

EPS = 1e-8
CSF, GM, WM = TISSUE_CLASSES  # 1, 2, 3
STRUCT = ndimage.generate_binary_structure(3, 1)  # 6-connexité


def n_learned_params(steps: list[str] | None = None) -> int:
    """Zéro, par construction : aucun seuil de ce module n'est calibré sur les labels."""
    return 0


# --- Étapes -------------------------------------------------------------------------------


def smooth_proba(proba: np.ndarray, mask: np.ndarray, spacing: tuple) -> np.ndarray:
    """Lissage gaussien des probabilités, normalisé par le masque (bord non dilué).

    Le numérateur et le dénominateur sont lissés séparément, comme dans le bloc gaussien des
    features : sans cette normalisation, les voxels proches du bord du masque verraient leurs
    probabilités tirées vers zéro par le fond, ce qui déplacerait la frontière du LCR.
    """
    sigma = tuple(SMOOTH_SIGMA_MM / float(s) for s in spacing)
    m = mask.astype(np.float32)
    weight = ndimage.gaussian_filter(m, sigma=sigma, mode="constant")
    out = np.empty_like(proba, dtype=np.float32)
    for c in range(proba.shape[-1]):
        num = ndimage.gaussian_filter(proba[..., c].astype(np.float32) * m, sigma=sigma, mode="constant")
        out[..., c] = num / np.maximum(weight, EPS)
    out *= mask[..., None]
    total = out.sum(axis=-1, keepdims=True)
    return np.divide(out, total, out=np.zeros_like(out), where=total > EPS)


def _voxel_volume(spacing: tuple) -> float:
    return float(spacing[0] * spacing[1] * spacing[2])


def remove_small_components(seg: np.ndarray, proba: np.ndarray, mask: np.ndarray, spacing: tuple) -> np.ndarray:
    """Retire les composantes 6-connexes de volume < MIN_COMPONENT_MM3 et réattribue.

    Un voxel retiré ne devient pas du fond : il repasse à la classe la plus probable parmi
    celles qui restent, ce qui préserve la partition du masque en trois tissus.
    """
    min_voxels = max(1, int(round(MIN_COMPONENT_MM3 / _voxel_volume(spacing))))
    seg = seg.copy()
    p = proba.copy()
    for c in TISSUE_CLASSES:
        comp, n = ndimage.label(seg == c, structure=STRUCT)
        if n == 0:
            continue
        sizes = np.bincount(comp.reshape(-1))
        small = np.flatnonzero(sizes < min_voxels)
        small = small[small != 0]
        if small.size == 0:
            continue
        drop = np.isin(comp, small)
        p[drop, c - 1] = -1.0  # cette classe n'est plus éligible pour ces voxels
        seg[drop] = (np.argmax(p[drop], axis=-1) + 1).astype(np.uint8)
    seg[~mask] = 0
    return seg


def fill_wm_holes(seg: np.ndarray, mask: np.ndarray) -> np.ndarray:
    """Bouche les cavités entièrement entourées de substance blanche.

    Une poche de LCR ou de matière grise strictement incluse dans la substance blanche, sans
    aucun chemin vers l'extérieur, n'existe pas dans un cerveau de nourrisson à cette échelle.
    Seules les cavités fermées sont concernées : les ventricules, qui communiquent, ne le sont
    pas.
    """
    wm = seg == WM
    filled = ndimage.binary_fill_holes(wm, structure=STRUCT)
    seg = seg.copy()
    seg[filled & ~wm & mask] = WM
    seg[~mask] = 0
    return seg


def _violations(seg: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """(voxels SB 6-adjacents à du LCR, voxels LCR 6-adjacents à de la SB)."""
    csf, wm = seg == CSF, seg == WM
    csf_dil = ndimage.binary_dilation(csf, structure=STRUCT)
    wm_dil = ndimage.binary_dilation(wm, structure=STRUCT)
    return wm & csf_dil, csf & wm_dil


def enforce_gm_between(seg: np.ndarray, proba: np.ndarray, mask: np.ndarray) -> np.ndarray:
    """Interdit tout contact 6-connexe entre substance blanche et LCR.

    Au cortex, le ruban gris s'interpose entre les deux et un contact direct est soit une
    erreur de classification, soit une frontière déplacée d'un voxel. Aux ventricules, en
    revanche, le contact est RÉEL : la substance blanche périventriculaire borde le LCR sans
    matière grise intermédiaire. Appliquer la règle partout dégrade donc la segmentation, ce
    que la mesure confirme ; voir l'avertissement en tête de module. On le répare du côté le
    moins sûr. La MARGE d'un voxel est l'écart entre la probabilité de sa classe et celle de
    la matière grise : plus elle est faible, moins le voxel « tient » à sa classe. À chaque
    passe, un voxel en infraction devient gris si sa marge n'excède celle d'aucun de ses
    voisins en infraction du camp d'en face.

    Cette règle locale ne garantit PAS à elle seule de résorber chaque contact à chaque passe.
    Un voxel de substance blanche touchant deux voxels de LCR de marges plus faibles ne bascule
    pas, et ces deux-là peuvent eux aussi être retenus par un troisième voisin : la
    configuration se bloque sans que le reste du volume cesse de progresser. Le cas est rare —
    il s'est produit sur un sujet des dix — mais il existe, et une contrainte qui ne tient que
    la plupart du temps ne vaut rien.

    D'où la PASSE FORCÉE finale : une fois les passes à la marge épuisées, tout voxel de
    substance blanche encore au contact du LCR devient gris, sans condition. Elle résout
    nécessairement tout ce qui reste, puisque par définition il ne subsiste alors aucun voxel
    de substance blanche adjacent à du LCR. La terminaison est donc démontrée, pas constatée ;
    les passes à la marge servent seulement à trancher intelligemment tant que c'est possible.
    """
    seg = seg.copy()
    margin = np.where(seg == WM, proba[..., WM - 1], proba[..., CSF - 1]) - proba[..., GM - 1]
    for _ in range(MAX_GM_BETWEEN_PASSES):
        viol_wm, viol_csf = _violations(seg)
        if not (viol_wm.any() or viol_csf.any()):
            return seg
        big = margin.max() + 1.0
        # marge minimale parmi les voisins en infraction du camp opposé
        opp_wm = np.where(viol_csf, margin, big)
        opp_csf = np.where(viol_wm, margin, big)
        min_opp_for_wm = ndimage.minimum_filter(opp_wm, footprint=STRUCT, mode="constant", cval=big)
        min_opp_for_csf = ndimage.minimum_filter(opp_csf, footprint=STRUCT, mode="constant", cval=big)
        flip = (viol_wm & (margin <= min_opp_for_wm)) | (viol_csf & (margin <= min_opp_for_csf))
        if not flip.any():
            break
        seg[flip & mask] = GM
        margin = np.where(flip, np.inf, margin)

    viol_wm, _ = _violations(seg)
    if viol_wm.any():
        seg[viol_wm & mask] = GM  # passe forcée : résout tout ce qui reste, par construction
    residuel_wm, residuel_csf = _violations(seg)
    if residuel_wm.any() or residuel_csf.any():  # ne peut pas arriver ; filet, pas espoir
        raise RuntimeError(
            f"gm_between : {int(residuel_wm.sum())} contacts subsistent après la passe forcée, "
            "ce qui contredit sa définition"
        )
    return seg


# --- Orchestration ------------------------------------------------------------------------

STEPS = ("smooth", "small_components", "fill_wm_holes", "gm_between")


def apply_postproc(proba_vol: np.ndarray, mask: np.ndarray, spacing: tuple, steps: list[str]) -> np.ndarray:
    """Applique les étapes DANS L'ORDRE DONNÉ et rend un volume d'étiquettes uint8.

    `proba_vol` est (D, H, W, 3) float, `mask` est (D, H, W) bool, `steps` une liste de noms
    pris dans STEPS. Une liste vide équivaut à l'argmax nu, ce que fait déjà la boucle LOO
    quand aucun post-traitement n'est demandé.
    """
    unknown = [s for s in steps if s not in STEPS]
    if unknown:
        raise KeyError(f"étape(s) de post-traitement inconnue(s) : {unknown}, disponibles : {list(STEPS)}")
    proba = np.asarray(proba_vol, dtype=np.float32)
    if proba.shape[:3] != mask.shape or proba.shape[3] != 3:
        raise ValueError(f"proba {proba.shape} incompatible avec mask {mask.shape}")

    if "smooth" in steps:  # agit sur les probabilités, donc avant l'argmax
        proba = smooth_proba(proba, mask, spacing)
    seg = (np.argmax(proba, axis=-1) + 1).astype(np.uint8)
    seg[~mask] = 0
    for step in steps:
        if step == "smooth":
            continue
        if step == "small_components":
            seg = remove_small_components(seg, proba, mask, spacing)
        elif step == "fill_wm_holes":
            seg = fill_wm_holes(seg, mask)
        elif step == "gm_between":
            seg = enforce_gm_between(seg, proba, mask)
    seg[~mask] = 0
    return seg
