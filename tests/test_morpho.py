import numpy as np
import pytest

from src.features.morpho import MorphoFeatures, build_tree, first_ancestor_with_area, node_attributes, rank_quantize
from src.io import Subject


def concentric(shape=(41, 41, 41), radii=(15, 8), levels=(2, 1)):
    z, y, x = np.mgrid[: shape[0], : shape[1], : shape[2]]
    r = np.sqrt((z - 20) ** 2 + (y - 20) ** 2 + (x - 20) ** 2)
    q = np.zeros(shape, dtype=np.uint8)
    for rad, lev in zip(radii, levels):
        q[r < rad] = lev
    return q, r


def test_tree_depth_and_areas_on_concentric_spheres():
    q, r = concentric()
    (tree, alt), = build_tree(q)
    A = node_attributes(tree, alt, q.shape, levels=3, n_mask=q.size, extent_ref=41.0)
    center = np.ravel_multi_index((20, 20, 20), q.shape)
    inner = A["parents"][center]
    outer = A["parents"][inner]
    root = A["parents"][outer]
    assert A["area"][inner] == (r < 8).sum() and A["area"][outer] == (r < 15).sum()
    assert A["parents"][root] == root and A["area"][root] == q.size
    # les feuilles (un nœud par voxel) sont un cran sous leur forme propre : profondeur max = 3
    assert A["depth"][[root, outer, inner]].tolist() == [0.0, 1 / 3, 2 / 3]
    # sphéricité ~ 1 sur des sphères, niveau du nœud interne = 1/2 après normalisation par levels-1
    assert abs(A["spher"][inner] - 1) < 0.1 and abs(A["spher"][outer] - 1) < 0.1
    assert A["alt"][inner] == pytest.approx(0.5) and A["contrast"][inner] == pytest.approx(-0.5)


def test_first_ancestor_with_area():
    parents = np.array([2, 2, 4, 4, 4])
    area = np.array([1, 1, 2, 1, 3])
    start = np.array([0, 1, 3])
    assert first_ancestor_with_area(parents, area, start, 2).tolist() == [2, 2, 4]
    assert first_ancestor_with_area(parents, area, start, 100).tolist() == [4, 4, 4]


def _noisy_subject(seed=0):
    rng = np.random.default_rng(seed)
    q, r = concentric(levels=(60, 200))  # coquille sombre, cœur clair
    mask = r < 18
    img = (q.astype(np.float32) + rng.normal(0, 8, q.shape)) * mask + 100 * (~mask)
    return Subject(t1=img, t2=(300 - img) * mask, label=mask.astype(np.uint8), mask=mask, subject_id=1, spacing=(1.0, 1.0, 1.0)), rng


def test_self_duality():
    """Les features de f et de max(f) - f sont identiques (signées : opposées)."""
    s, _ = _noisy_subject()
    f = MorphoFeatures(levels=64, area_profile=(50, 500), grain_filters=(20,))
    q = f.quantize(s.t1, s.mask)
    q_dual = (f.levels - 1 - q.astype(np.int64)).astype(q.dtype)
    Xa = np.stack(f.features_from_quantized(q, s.mask), 1)
    Xb = np.stack(f.features_from_quantized(q_dual, s.mask), 1)
    names = [n[3:] for n in f.names if n.startswith("t1_")]
    signed = [i for i, n in enumerate(names) if n.endswith("contrast") or n.endswith("resid")]
    unsigned = [i for i in range(len(names)) if i not in signed]
    assert np.allclose(Xa[:, unsigned], Xb[:, unsigned], atol=1e-5)
    assert np.allclose(Xa[:, signed], -Xb[:, signed], atol=1e-5)


def test_invariance_to_increasing_transform():
    s, _ = _noisy_subject()
    f = MorphoFeatures(levels=64, area_profile=(50,), grain_filters=(20,))
    Xa = f.transform(s)
    v = s.t1 - s.t1.min()
    s.t1 = (v / v.max()) ** 1.7 * 1000
    s.t2 = np.exp(s.t2 / 300)
    Xb = f.transform(s)
    assert np.array_equal(Xa, Xb)


def test_output_shape_order_and_zero_params():
    s, _ = _noisy_subject()
    f = MorphoFeatures(levels=64, area_profile=(50, 500), grain_filters=(20, 200))
    X = f.transform(s)
    assert X.shape == (s.mask.sum(), len(f.names)) and X.dtype == np.float32
    assert len(f.names) == 2 * (6 + 2 * 5 + 2) and f.n_learned_params == 0
    assert np.isfinite(X).all()
    # l'ordre des voxels est celui de np.flatnonzero(mask), commun à tous les blocs
    z, y, x = np.mgrid[tuple(slice(d) for d in s.mask.shape)]
    core = (np.sqrt((z - 20) ** 2 + (y - 20) ** 2 + (x - 20) ** 2) < 6).reshape(-1)[np.flatnonzero(s.mask)]
    # le cœur clair du T1 est plus clair que son ancêtre de volume >= 500 (résidu > 0),
    # et plus sombre dans le T2 au contraste inversé
    assert X[core, f.names.index("t1_tos_a500_resid")].mean() > 0
    assert X[core, f.names.index("t2_tos_a500_resid")].mean() < 0
    # les formes propres du cœur sont bien plus petites que le masque : log10(aire / |masque|) < 0
    assert X[core, f.names.index("t1_tos_area_log")].mean() < 0


def test_minmax_fallback_doubles_features_and_matches_interface():
    s, _ = _noisy_subject()
    f = MorphoFeatures(levels=64, area_profile=(500,), grain_filters=(), tree="minmax")
    X = f.transform(s)
    assert len(f.names) == 2 * 2 * (6 + 5) and X.shape == (s.mask.sum(), len(f.names))
    assert f.names[0] == "t1_maxt_area_log" and "t1_mint_area_log" in f.names
    assert f.n_learned_params == 0 and np.isfinite(X).all()


def test_rank_quantize_fills_outside_with_median():
    vol = np.arange(27, dtype=np.float32).reshape(3, 3, 3)
    mask = vol >= 9
    q = rank_quantize(vol, mask, 8)
    assert q[~mask].min() == q[~mask].max() == int(np.median(q[mask]))
    assert q[mask].min() == 0 and q[mask].max() == 7
