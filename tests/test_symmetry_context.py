import numpy as np

from src.features.context import ContextFeatures
from src.features.symmetry import SymmetryFeatures, mirror_coordinates
from tests.test_spatial import ellipsoid_subject


def test_mirror_of_symmetric_image_is_identity():
    s = ellipsoid_subject()
    # image symétrique par rapport au plan x = centre : t1 = t1[::-1]
    z, y, x = np.mgrid[: s.mask.shape[0], : s.mask.shape[1], : s.mask.shape[2]].astype(np.float32)
    img = (np.abs(z - s.mask.shape[0] / 2) + y) * s.mask  # symétrique autour du centroïde
    s.t1 = img
    s.t2 = img
    X = SymmetryFeatures().transform(s)
    assert X.shape == (s.mask.sum(), 4)
    assert np.abs(X[:, 1]).mean() < 0.05  # voxel - miroir ~ 0 partout


def test_mirror_coordinates_are_reflections():
    s = ellipsoid_subject()
    mc = mirror_coordinates(s)
    idx = np.stack(np.nonzero(s.mask), 1)
    # le miroir du miroir est le point de départ
    assert np.allclose(mc.T[:, 1:], idx[:, 1:], atol=1.0)
    assert np.allclose(mc.T[:, 0], s.mask.shape[0] - 1 - idx[:, 0], atol=1.0)


def test_context_block():
    s = ellipsoid_subject()
    rng = np.random.default_rng(0)
    s.t1 = rng.random(s.mask.shape).astype(np.float32) * s.mask
    s.t2 = s.t1.copy()
    f = ContextFeatures(radii=(1, 2))
    X = f.transform(s)
    assert X.shape == (s.mask.sum(), 8) and len(f.names) == 8 and f.n_learned_params == 0
    # rangs uniformes : moyenne locale ~ 0.5, écart-type ~ 1/sqrt(12)
    assert abs(X[:, 0].mean() - 0.5) < 0.02 and abs(X[:, 1].mean() - 12**-0.5) < 0.05
    assert X.min() >= 0 and X.max() <= 1
