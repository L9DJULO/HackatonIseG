import numpy as np

from src.features.morpho import MorphoFeatures, first_ancestor_with_area, rank_quantize
from src.io import Subject


def test_rank_quantize_invariant_to_monotone_transform():
    rng = np.random.default_rng(0)
    vol = rng.random((8, 9, 10)).astype(np.float32)
    mask = vol > 0.1
    a = rank_quantize(vol, mask, 64)
    b = rank_quantize(np.exp(3 * vol) * 17, mask, 64)
    assert np.array_equal(a, b)
    assert a[~mask].max() == 0 and a[mask].min() >= 1 and a.max() <= 63


def test_first_ancestor_with_area():
    # arbre : 0,1 -> 2 ; 2,3 -> 4 (racine)
    parents = np.array([2, 2, 4, 4, 4])
    area = np.array([1, 1, 2, 1, 3])
    start = np.array([0, 1, 3])
    assert first_ancestor_with_area(parents, area, start, 2).tolist() == [2, 2, 4]
    assert first_ancestor_with_area(parents, area, start, 100).tolist() == [4, 4, 4]


def test_morpho_block_on_nested_blobs():
    rng = np.random.default_rng(0)
    shape = (30, 32, 34)
    z, y, x = np.mgrid[: shape[0], : shape[1], : shape[2]].astype(np.float32)
    r = np.sqrt((z - 15) ** 2 + (y - 16) ** 2 + (x - 17) ** 2)
    mask = r < 13
    img = np.where(r < 5, 300, np.where(r < 9, 200, 100)).astype(np.float32) + rng.normal(0, 3, shape)
    img *= mask
    s = Subject(t1=img, t2=(400 - img) * mask, label=mask.astype(np.uint8), mask=mask, subject_id=1, spacing=(1.0, 1.0, 1.0))
    f = MorphoFeatures(area_profile=(50, 500), area_filters=(20, 200))
    X = f.transform(s)
    assert X.shape == (mask.sum(), 2 * (6 + 2 * 3 + 2 * 2)) and X.dtype == np.float32
    assert f.n_learned_params == 0 and len(f.names) == X.shape[1]
    names = f.names
    core = np.flatnonzero(mask) == np.ravel_multi_index((15, 16, 17), shape)
    # le coeur brillant du T1 est plus clair que son ancêtre de volume >= 500 (résidu > 0),
    # et plus sombre dans le T2 inversé (résidu < 0) ; la hauteur de l'ancêtre est > 0
    assert X[core][0, names.index("t1_tos_a500_resid")] > 0
    assert X[core][0, names.index("t2_tos_a500_resid")] < 0
    assert X[core][0, names.index("t1_tos_a500_height")] > 0
    assert np.isfinite(X).all()
