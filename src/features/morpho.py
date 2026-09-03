"""BLOC D — attributs morphologiques par arbres de composantes (higra). 0 paramètre appris.

Prétraitement (par sujet, par modalité) : l'image est quantifiée sur 256 niveaux PAR RANG à
l'intérieur du masque (égalisation d'histogramme), 0 hors masque. Les arbres ne dépendent
que de l'ordre des intensités : ils sont ainsi invariants à tout changement de gain monotone
d'un sujet à l'autre. Calcul sur la boîte englobante du masque (identique, plus rapide).

1) ARBRE DES FORMES (tree of shapes, hg.component_tree_tree_of_shapes_image3d, 6-connexité
   avec immersion Khalimsky) : pour chaque voxel, on remonte à la plus petite forme qui le
   contient et on lit :
     tos_area_log   : log10 de son volume (voxels)
     tos_depth      : sa profondeur dans l'arbre / profondeur max
     tos_contrast   : contraste signé avec la forme parente (niveau de la forme - niveau du parent)
     tos_height     : hauteur (dynamique) de la sous-arborescence
     tos_compact    : volume / volume de la boîte englobante
     tos_extent_log : log10 de la plus grande extension de la boîte englobante
   puis PROFIL D'ATTRIBUTS : pour chaque seuil d'aire A dans area_profile, on remonte au
   premier ANCÊTRE de volume >= A et on lit sa hauteur (dynamique), la différence de
   niveau entre le voxel et cet ancêtre (résidu multi-échelle) et sa compacité.
   (Le contraste ancêtre/parent vaut presque toujours 1 niveau dans un arbre aussi
   finement imbriqué : il est remplacé par la hauteur, vérifié sur le sujet 1.) C'est une
   description du contexte morphologique à plusieurs échelles, en volume et non en pixels.

2) OUVERTURES / FERMETURES PAR ATTRIBUT D'AIRE (max-tree / min-tree, 6-connexité) aux
   seuils area_filters : résidus image - ouverture (top-hat blanc) et fermeture - image
   (top-hat noir), normalisés dans [0, 1].

Hyperparamètres fixés a priori : levels=256, area_profile=(100, 1000, 10000),
area_filters=(50, 500, 5000). Aucun n'est ajusté sur les labels.
"""
from __future__ import annotations

import numpy as np

from src.features.base import FeatureExtractor
from src.features.gaussian import mask_bbox
from src.io import Subject


def rank_quantize(vol: np.ndarray, mask: np.ndarray, levels: int = 256) -> np.ndarray:
    """Égalisation d'histogramme dans le masque -> uint8 dans [1, levels-1], 0 hors masque."""
    v = vol[mask]
    order = np.argsort(v, kind="stable")
    ranks = np.empty(v.size, dtype=np.float64)
    ranks[order] = np.arange(v.size)
    q = 1 + np.floor(ranks / v.size * (levels - 1)).astype(np.uint8)
    out = np.zeros(vol.shape, dtype=np.uint8)
    out[mask] = q
    return out


def first_ancestor_with_area(parents: np.ndarray, area: np.ndarray, start: np.ndarray, min_area: int) -> np.ndarray:
    """Pour chaque noeud de départ, premier ancêtre (lui compris) de volume >= min_area. Vectorisé."""
    cur = start.copy()
    while True:
        small = area[cur] < min_area
        if not small.any():
            return cur
        nxt = parents[cur[small]]
        if np.array_equal(nxt, cur[small]):  # racine atteinte
            return cur
        cur[small] = nxt


def _bbox_attributes(tree, shape: tuple[int, ...]):
    import higra as hg

    n = int(np.prod(shape))
    coords = np.stack(np.unravel_index(np.arange(n), shape), axis=1).astype(np.float32)
    mx = hg.accumulate_sequential(tree, coords, hg.Accumulators.max)
    mn = hg.accumulate_sequential(tree, coords, hg.Accumulators.min)
    extent = mx - mn + 1.0
    bbox_vol = np.prod(extent, axis=1)
    return bbox_vol, extent.max(axis=1)


class MorphoFeatures(FeatureExtractor):
    name = "morpho"

    def __init__(
        self,
        levels: int = 256,
        area_profile=(100, 1000, 10000),
        area_filters=(50, 500, 5000),
        modalities=("t1", "t2"),
    ):
        self.levels = int(levels)
        self.area_profile = tuple(int(a) for a in area_profile)
        self.area_filters = tuple(int(a) for a in area_filters)
        self.modalities = tuple(modalities)

    @property
    def config(self) -> dict:
        return {
            "levels": self.levels,
            "area_profile": list(self.area_profile),
            "area_filters": list(self.area_filters),
            "modalities": list(self.modalities),
            "quantization": "rank_in_mask",
            "adjacency": 6,
        }

    @property
    def names(self) -> list[str]:
        out = []
        for mod in self.modalities:
            out += [f"{mod}_tos_{k}" for k in ("area_log", "depth", "contrast", "height", "compact", "extent_log")]
            for a in self.area_profile:
                out += [f"{mod}_tos_a{a}_{k}" for k in ("height", "resid", "compact")]
            for a in self.area_filters:
                out += [f"{mod}_tophat_white_a{a}", f"{mod}_tophat_black_a{a}"]
        return out

    def _tos_features(self, q: np.ndarray) -> list[np.ndarray]:
        import higra as hg

        tree, alt = hg.component_tree_tree_of_shapes_image3d(q, padding="zero", original_size=True, immersion=True)
        alt = alt.astype(np.float32) / (self.levels - 1)
        parents = tree.parents()
        n_leaves = q.size
        node = parents[:n_leaves]  # plus petite forme contenant chaque voxel
        area = hg.attribute_area(tree).astype(np.float32)
        depth = hg.attribute_depth(tree).astype(np.float32)
        height = hg.attribute_height(tree, alt).astype(np.float32)
        bbox_vol, extent_max = _bbox_attributes(tree, q.shape)
        contrast = alt - alt[parents]
        compact = area / np.maximum(bbox_vol, 1.0)
        feats = [
            np.log10(area[node]),
            depth[node] / max(depth.max(), 1.0),
            contrast[node],
            height[node],
            compact[node],
            np.log10(extent_max[node]),
        ]
        leaf_alt = alt[:n_leaves]
        for a in self.area_profile:
            anc = first_ancestor_with_area(parents, area, node, a)
            feats += [height[anc], leaf_alt - alt[anc], compact[anc]]
        return [f.astype(np.float32) for f in feats]

    def _area_filter_features(self, q: np.ndarray) -> list[np.ndarray]:
        import higra as hg

        g = hg.get_6_adjacency_graph(q.shape)
        img = q.astype(np.float32) / (self.levels - 1)
        feats = []
        maxt, malt = hg.component_tree_max_tree(g, q)
        mint, nalt = hg.component_tree_min_tree(g, q)
        area_max = hg.attribute_area(maxt)
        area_min = hg.attribute_area(mint)
        for a in self.area_filters:
            opened = hg.reconstruct_leaf_data(maxt, malt, area_max < a).astype(np.float32) / (self.levels - 1)
            closed = hg.reconstruct_leaf_data(mint, nalt, area_min < a).astype(np.float32) / (self.levels - 1)
            feats += [img - opened, closed - img]
        return feats

    def transform(self, subject: Subject) -> np.ndarray:
        crop = mask_bbox(subject.mask, 1)
        mask_c = subject.mask[crop]
        cols: list[np.ndarray] = []
        for mod in self.modalities:
            q = rank_quantize(getattr(subject, mod)[crop], mask_c, self.levels)
            flat_sel = mask_c.reshape(-1)
            cols += [f.reshape(-1)[flat_sel] for f in self._tos_features(q)]
            cols += [f.reshape(-1)[flat_sel] for f in self._area_filter_features(q)]
        X = np.stack(cols, axis=1).astype(np.float32)
        return self._check(subject, X)


BLOCKS = (MorphoFeatures,)
