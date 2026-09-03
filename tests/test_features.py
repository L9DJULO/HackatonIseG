import numpy as np

from src.features.intensity import IntensityFeatures, percentile_rank
from src.features.registry import build_extractor
from tests.test_sampling import toy_subject


def test_percentile_rank():
    r = percentile_rank(np.array([3.0, 1.0, 2.0]))
    assert r.tolist() == [1.0, 0.0, 0.5]


def test_intensity_block_shape_and_zero_params():
    s = toy_subject()
    f = IntensityFeatures()
    X = f.transform(s)
    assert X.shape == (s.mask.sum(), 6) and X.dtype == np.float32
    assert f.n_learned_params == 0 and len(f.names) == 6
    assert abs(X[:, 0].mean()) < 1e-4 and abs(X[:, 0].std() - 1) < 1e-3


def test_cache_roundtrip(tmp_path):
    s = toy_subject()
    ext = build_extractor([{"name": "intensity"}], cache_dir=tmp_path, verbose=False)
    X1 = np.asarray(ext.transform(s))
    assert ext.blocks[0].path(99).exists()
    X2 = np.asarray(ext.transform(s))
    assert np.array_equal(X1, X2)
    rows = np.array([5, 1, 3])
    assert np.array_equal(ext.transform_rows(s, rows), X1[np.sort(rows)])
    assert ext.names[0] == "intensity/t1_z"
