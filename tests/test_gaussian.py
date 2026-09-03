import numpy as np
from scipy import ndimage

from src.features.gaussian import GaussianFeatures, mask_bbox, sym3x3_eigvals_sorted_abs
from src.io import Subject


def test_eigvals_match_numpy():
    rng = np.random.default_rng(0)
    n = 2000
    m = rng.normal(size=(n, 3, 3))
    m = (m + m.transpose(0, 2, 1)) / 2
    m[:10] = np.eye(3)[None] * 2.5  # cas dégénéré p == 0
    ref = np.linalg.eigvalsh(m)
    ref = np.take_along_axis(ref, np.argsort(np.abs(ref), axis=1), axis=1)
    got = sym3x3_eigvals_sorted_abs(m[:, 0, 0], m[:, 1, 1], m[:, 2, 2], m[:, 0, 1], m[:, 0, 2], m[:, 1, 2])
    assert np.allclose(np.sort(got, 1), np.sort(ref, 1), atol=1e-8)
    assert np.allclose(np.abs(got), np.sort(np.abs(ref), 1), atol=1e-8)


def _blob_subject(rot: bool):
    z, y, x = np.mgrid[:40, :48, :44].astype(np.float32)
    c = np.array([20, 24, 22])
    # ellipsoïde allongé ; version "tournée" = axes permutés (rotation de 90°)
    if rot:
        v = ((x - c[2]) / 6) ** 2 + ((y - c[1]) / 12) ** 2 + ((z - c[0]) / 6) ** 2
    else:
        v = ((x - c[2]) / 12) ** 2 + ((y - c[1]) / 6) ** 2 + ((z - c[0]) / 6) ** 2
    img = np.exp(-v).astype(np.float32) * 100
    mask = v < 4
    lab = np.where(mask, 2, 0).astype(np.uint8)
    return Subject(t1=img * mask, t2=img * mask, label=lab, mask=mask, subject_id=1, spacing=(1.0, 1.0, 1.0))


def test_gaussian_block_shape_names_rotation_invariance():
    f = GaussianFeatures(sigmas_mm=(1.0, 2.0), modalities=("t1",))
    assert f.n_features == 2 * 6 + 1 and f.n_learned_params == 0
    a, b = _blob_subject(False), _blob_subject(True)
    Xa, Xb = f.transform(a), f.transform(b)
    assert Xa.shape == (a.mask.sum(), 13) and Xa.dtype == np.float32
    # Les valeurs propres triées au centre doivent être identiques à rotation près.
    ca = np.flatnonzero(a.mask) == np.ravel_multi_index((20, 24, 22), a.mask.shape)
    cb = np.flatnonzero(b.mask) == np.ravel_multi_index((20, 24, 22), b.mask.shape)
    assert np.allclose(Xa[ca][0, 3:6], Xb[cb][0, 3:6], rtol=2e-2, atol=1e-3)
    assert np.allclose(Xa[ca][0, :3], Xb[cb][0, :3], rtol=2e-2, atol=1e-3)


def test_mask_bbox():
    m = np.zeros((10, 10, 10), dtype=bool)
    m[3:5, 2:8, 9] = True
    assert mask_bbox(m, 1) == (slice(2, 6), slice(1, 9), slice(8, 10))
