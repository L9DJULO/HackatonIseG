import numpy as np

from src.features.spatial import SpatialFeatures, principal_axes
from src.io import Subject


def ellipsoid_subject(rx=20, ry=30, rz=25, shape=(60, 80, 70)):
    z, y, x = np.mgrid[: shape[0], : shape[1], : shape[2]].astype(np.float64)
    c = np.array(shape) / 2
    v = ((z - c[0]) / rx) ** 2 + ((y - c[1]) / ry) ** 2 + ((x - c[2]) / rz) ** 2
    mask = v <= 1
    img = mask.astype(np.float32)
    return Subject(t1=img, t2=img, label=mask.astype(np.uint8), mask=mask, subject_id=1, spacing=(1.0, 1.0, 1.0))


def test_principal_axes_orientation_convention():
    s = ellipsoid_subject()
    coords = np.stack(np.nonzero(s.mask), 1).astype(float)
    c, axes = principal_axes(coords)
    assert np.allclose(c, np.array(s.mask.shape) / 2 - 0.5 + 0.5, atol=1.0)
    # axes ~ identité (chaque axe PCA renvoyé sur l'axe image le plus proche, signe positif)
    assert np.allclose(np.abs(axes), np.eye(3), atol=0.05)
    assert (np.diag(axes) > 0).all()


def test_spatial_features_ranges_and_symmetry():
    s = ellipsoid_subject()
    X = SpatialFeatures().transform(s)
    assert X.shape == (s.mask.sum(), 9) and X.dtype == np.float32
    assert X[:, :7].min() >= 0 and X[:, :7].max() <= 1 + 1e-6
    assert -1 - 1e-6 <= X[:, 7].min() and X[:, 7].max() <= 1 + 1e-6
    # symétrie gauche/droite (axe 0) : dist_midsag identique pour un voxel et son miroir
    vol = np.zeros(s.mask.shape, dtype=np.float32)
    vol[s.mask] = X[:, 5]
    flipped = vol[::-1]
    sel = s.mask & s.mask[::-1]
    assert np.allclose(vol[sel], flipped[sel], atol=0.05)
    # le centre est à dist_border max (1) et r_norm ~ 0
    center = tuple(d // 2 for d in s.mask.shape)
    row = np.flatnonzero(s.mask) == np.ravel_multi_index(center, s.mask.shape)
    assert X[row][0, 4] > 0.95 and X[row][0, 6] < 0.05
