"""BLOC D — contexte morphologique non local par ARBRE DES FORMES 3D (higra). 0 paramètre appris.

PAS DE FUITE : tout ce qui suit se calcule sur le sujet lui-même (quantification, arbre,
attributs, normalisations). Aucune statistique inter-sujets, aucun seuil ajusté sur les labels.
`n_learned_params` vaut 0.

Pourquoi l'arbre des formes : (1) auto-dualité, l'arbre de f et de -f sont identiques, donc T1
et T2 (contrastes inversés) sont traités de la même façon ; (2) invariance à toute
transformation croissante de l'intensité ; (3) chaque voxel appartient à une branche complète,
de sa plus petite forme jusqu'à la racine, que l'on remonte pour lire des descripteurs à toutes
les échelles anatomiques sans un seul poids appris.

Prétraitement (par sujet, par modalité)
  - recadrage sur la boîte englobante du masque + 1 voxel ;
  - quantification sur `levels` niveaux, deux variantes MESURÉES en leave-one-out :
      "linear" (défaut) = niveaux linéaires entre les percentiles 1 et 99 intra-masque. Invariante
        aux transformations affines de l'intensité (gain et offset d'acquisition), et elle
        PRÉSERVE les amplitudes de contraste, ce qui rend les contrastes et résidus de l'arbre
        plus informatifs. Dice moyen 0.8176.
      "rank" = rang percentile intra-masque, invariante à TOUTE transformation croissante, y
        compris non linéaire (gamma), mais elle égalise les amplitudes de contraste et perd donc
        de l'information. Dice moyen 0.8148.
    On garde "linear" par défaut : le gain mesuré est réel et les volumes iSeg sont déjà corrigés
    en inhomogénéité de champ, donc l'invariance non linéaire n'est pas nécessaire ici. La
    structure de l'arbre reste invariante par transformation croissante dans les deux cas ;
  - voxels hors masque remplacés par la MÉDIANE intra-masque, pour ne pas créer de forme géante
    de fond ; bordure d'un voxel à la même valeur (padding higra "none").

Arbre (option `tree`)
  "tos"    arbre des formes, hg.component_tree_tree_of_shapes_image3d, immersion Khalimsky
           6-connexe, une feuille par voxel. Un seul arbre auto-dual par modalité.
  "minmax" max-tree ET min-tree 6-connexes (voie de repli, deux fois plus de features pour la
           même information : c'est la comparaison qui justifie le choix de l'arbre des formes).
Le "nœud propre" d'un voxel est la plus petite forme/composante qui le contient.

Attributs de nœud (tous sans dimension)
  area_log    log10(volume du nœud / volume du masque)
  depth       profondeur dans l'arbre / profondeur maximale
  contrast    niveau du nœud - niveau du parent, en fraction de l'étendue [0, levels-1] (signé)
  height      dynamique de la sous-arborescence : niveau max - niveau min des voxels qu'elle
              contient, même unité. On ne prend PAS hg.attribute_height, qui est signée par la
              direction du contraste et casserait donc l'auto-dualité (vérifié par les tests).
  spher       sphéricité (36 pi V^2)^(1/3) / (A / 1.5), A = nombre de faces de bord (6-connexité) ;
              le facteur 1.5 est le rapport moyen entre l'aire comptée par faces et l'aire
              euclidienne d'une surface d'orientation quelconque, vérifié ~1 sur une sphère
  extent      plus grande extension de la boîte englobante / plus grande extension du masque

Features par voxel et par modalité
  1. attributs de son nœud propre : area_log, depth, contrast, height, spher, extent   (6)
  2. remontée de branche : pour chaque seuil T de `area_profile`, premier ancêtre de volume >= T
     (récurrence anc_T[n] = n si aire[n] >= T sinon anc_T[parent[n]], vectorisée par sauts de
     pointeurs sur les NŒUDS) : area_log, height, resid = niveau du voxel - niveau de l'ancêtre,
     depth, spher                                                        (5 par seuil)
  3. filtres de grain auto-duaux (DÉSACTIVÉS par défaut) : on supprime les formes de volume < G
     pour G dans `grain_filters` et on reconstruit ; feature = image - image filtrée (1 par G).
     Mesuré sans effet (Dice 0.8148 avec, 0.8149 sans) : le résidu de la remontée de branche
     porte déjà la même information multi-échelle. Gardé en option, hors du jeu par défaut.

Valeurs fixées a priori (défaut) : tree = "tos", levels = 256, quantization = "linear",
area_profile = (100, 1000, 10000, 100000) voxels, grain_filters = () (désactivés),
modalities = (t1, t2), adjacence 6. Soit 2 x (6 + 4 x 5) = 52 features
(le double avec tree = "minmax"). levels = 64 au lieu de 256 ne change rien (Dice 0.8140).
"""
from __future__ import annotations

import numpy as np

from src.features.base import FeatureExtractor
from src.features.gaussian import mask_bbox
from src.io import Subject

VERSION = 2


def rank_quantize(vol: np.ndarray, mask: np.ndarray, levels: int = 256) -> np.ndarray:
    """Rang percentile intra-masque -> entiers dans [0, levels-1] ; hors masque = médiane."""
    v = vol[mask]
    order = np.argsort(v, kind="stable")
    ranks = np.empty(v.size, dtype=np.float64)
    ranks[order] = np.arange(v.size)
    q_in = np.floor(ranks / v.size * levels).astype(np.int64).clip(0, levels - 1)
    return _fill_outside(q_in, mask, levels)


def linear_quantize(vol: np.ndarray, mask: np.ndarray, levels: int = 256) -> np.ndarray:
    """Niveaux linéaires entre les percentiles 1 et 99 intra-masque ; hors masque = médiane."""
    v = vol[mask].astype(np.float64)
    lo, hi = np.percentile(v, [1, 99])
    q_in = np.floor((v - lo) / max(hi - lo, 1e-6) * (levels - 1)).astype(np.int64).clip(0, levels - 1)
    return _fill_outside(q_in, mask, levels)


def _fill_outside(q_in: np.ndarray, mask: np.ndarray, levels: int) -> np.ndarray:
    dtype = np.uint8 if levels <= 256 else np.uint16
    out = np.full(mask.shape, int(np.median(q_in)), dtype=dtype)
    out[mask] = q_in
    return out


def first_ancestor_with_area(parents: np.ndarray, area: np.ndarray, start: np.ndarray, min_area: float) -> np.ndarray:
    """Premier ancêtre (lui compris) de volume >= min_area, par sauts de pointeurs vectorisés."""
    cur = start.copy()
    while True:
        small = area[cur] < min_area
        if not small.any():
            return cur
        nxt = parents[cur[small]]
        if np.array_equal(nxt, cur[small]):  # racine
            return cur
        cur[small] = nxt


def build_tree(q: np.ndarray, kind: str = "tos") -> list[tuple]:
    """Arbres d'un volume quantifié DÉJÀ bordé. Retourne une liste de (tree, altitudes).

    "tos" -> un seul arbre des formes (auto-dual) ; "minmax" -> [max-tree, min-tree].
    """
    import higra as hg

    if kind == "tos":
        return [hg.component_tree_tree_of_shapes_image3d(q, padding="none", original_size=True, immersion=True)]
    if kind == "minmax":
        g = hg.get_6_adjacency_graph(q.shape)
        return [hg.component_tree_max_tree(g, q), hg.component_tree_min_tree(g, q)]
    raise ValueError(kind)


def node_attributes(tree, altitudes: np.ndarray, shape: tuple[int, ...], levels: int, n_mask: int, extent_ref: float) -> dict:
    import higra as hg

    parents = tree.parents()
    area = hg.attribute_area(tree).astype(np.float64)
    depth = hg.attribute_depth(tree).astype(np.float64)
    alt = altitudes.astype(np.float64) / (levels - 1)
    # dynamique auto-duale : étendue des niveaux de la sous-arborescence (max - min sur ses voxels)
    leaf_alt = alt[: tree.num_leaves()]
    height = hg.accumulate_sequential(tree, leaf_alt, hg.Accumulators.max) - hg.accumulate_sequential(
        tree, leaf_alt, hg.Accumulators.min
    )
    contour = hg.attribute_contour_length(tree).astype(np.float64)
    coords = np.stack(np.unravel_index(np.arange(int(np.prod(shape))), shape), axis=1).astype(np.float32)
    ext = hg.accumulate_sequential(tree, coords, hg.Accumulators.max) - hg.accumulate_sequential(tree, coords, hg.Accumulators.min) + 1.0
    return {
        "parents": parents,
        "area": area,
        "alt": alt,
        "area_log": np.log10(area / n_mask),
        "depth": depth / max(depth.max(), 1.0),
        "contrast": alt - alt[parents],
        "height": height,
        "spher": np.cbrt(36.0 * np.pi * area**2) / np.maximum(contour / 1.5, 1e-6),
        "extent": ext.max(axis=1) / extent_ref,
    }


class MorphoFeatures(FeatureExtractor):
    name = "morpho"

    def __init__(
        self,
        levels: int = 256,
        quantization: str = "linear",
        tree: str = "tos",
        area_profile=(100, 1000, 10000, 100000),
        grain_filters=(),
        modalities=("t1", "t2"),
        leaf_attributes: bool = True,
    ):
        if quantization not in ("rank", "linear"):
            raise ValueError(quantization)
        if tree not in ("tos", "minmax"):
            raise ValueError(tree)
        self.tree = tree
        self.levels = int(levels)
        self.quantization = quantization
        self.area_profile = tuple(int(a) for a in area_profile)
        self.grain_filters = tuple(int(a) for a in grain_filters)
        self.modalities = tuple(modalities)
        self.leaf_attributes = bool(leaf_attributes)

    @property
    def config(self) -> dict:
        return {
            "version": VERSION,
            "tree": self.tree,
            "levels": self.levels,
            "quantization": self.quantization,
            "area_profile": list(self.area_profile),
            "grain_filters": list(self.grain_filters),
            "modalities": list(self.modalities),
            "leaf_attributes": self.leaf_attributes,
            "outside_mask": "median",
            "adjacency": 6,
        }

    @property
    def tree_tags(self) -> tuple[str, ...]:
        return ("tos",) if self.tree == "tos" else ("maxt", "mint")

    @property
    def names(self) -> list[str]:
        out = []
        for mod in self.modalities:
            for tag in self.tree_tags:
                if self.leaf_attributes:
                    out += [f"{mod}_{tag}_{k}" for k in ("area_log", "depth", "contrast", "height", "spher", "extent")]
                for a in self.area_profile:
                    out += [f"{mod}_{tag}_a{a}_{k}" for k in ("area_log", "height", "resid", "depth", "spher")]
                for g in self.grain_filters:
                    out.append(f"{mod}_{tag}_grain{g}_resid")
        return out

    def quantize(self, vol: np.ndarray, mask: np.ndarray) -> np.ndarray:
        fn = rank_quantize if self.quantization == "rank" else linear_quantize
        return fn(vol, mask, self.levels)

    def features_from_quantized(self, q: np.ndarray, mask: np.ndarray) -> list[np.ndarray]:
        """Features (liste de vecteurs sur les voxels du masque, ordre C) d'un volume quantifié."""
        import higra as hg

        fill = int(np.median(q[mask]))
        qp = np.pad(q, 1, mode="constant", constant_values=fill)
        n_mask = int(mask.sum())
        extent_ref = float(max(mask.shape))
        sel = np.pad(mask, 1, mode="constant", constant_values=False).reshape(-1)
        leaves = np.flatnonzero(sel)
        feats: list[np.ndarray] = []
        for tree, alt in build_tree(qp, self.tree):
            A = node_attributes(tree, alt, qp.shape, self.levels, n_mask, extent_ref)
            node = A["parents"][leaves]  # nœud propre de chaque voxel du masque
            leaf_alt = A["alt"][leaves]
            if self.leaf_attributes:
                feats += [A[k][node] for k in ("area_log", "depth", "contrast", "height", "spher", "extent")]
            for a in self.area_profile:
                anc = first_ancestor_with_area(A["parents"], A["area"], node, a)
                feats += [A["area_log"][anc], A["height"][anc], leaf_alt - A["alt"][anc], A["depth"][anc], A["spher"][anc]]
            for g in self.grain_filters:
                filtered = hg.reconstruct_leaf_data(tree, alt, A["area"] < g).astype(np.float64) / (self.levels - 1)
                feats.append(leaf_alt - filtered.reshape(-1)[leaves])
        return [f.astype(np.float32) for f in feats]

    def transform(self, subject: Subject) -> np.ndarray:
        crop = mask_bbox(subject.mask, 1)
        mask_c = subject.mask[crop]
        cols: list[np.ndarray] = []
        for mod in self.modalities:
            q = self.quantize(getattr(subject, mod)[crop], mask_c)
            cols += self.features_from_quantized(q, mask_c)
        return self._check(subject, np.stack(cols, axis=1))


BLOCKS = (MorphoFeatures,)
