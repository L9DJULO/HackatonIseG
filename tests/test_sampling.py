import numpy as np
import pytest

from src.io import Subject
from src.sampling import adjust_priors, boundary_mask, class_priors, sample_voxels


def toy_subject(seed=0):
    rng = np.random.default_rng(seed)
    label = np.zeros((12, 12, 12), dtype=np.uint8)
    label[2:10, 2:10, 2:10] = 1
    label[3:9, 3:9, 3:9] = 2
    label[4:8, 4:8, 4:8] = 3
    mask = label != 0
    t1 = rng.random(label.shape).astype(np.float32) * mask
    return Subject(t1=t1, t2=t1.copy(), label=label, mask=mask, subject_id=99, spacing=(1.0, 1.0, 1.0))


def test_boundary_mask_is_between_classes():
    s = toy_subject()
    b = boundary_mask(s.label, s.mask)
    assert b[4, 4, 4]  # WM touchant GM
    assert not b[5, 5, 5]  # centre du WM : tous les voisins sont WM
    assert b[2, 5, 5]  # CSF touchant GM
    # coin de CSF : voisins CSF ou fond -> pas frontière
    assert not b[2, 2, 2]


def test_sample_balanced_and_reproducible():
    s = toy_subject()
    idx, y = sample_voxels(s, 20, np.random.default_rng(0))
    assert idx.shape == y.shape == (60,)
    assert [int((y == c).sum()) for c in (1, 2, 3)] == [20, 20, 20]
    assert np.array_equal(s.mask_labels[idx], y)
    idx2, y2 = sample_voxels(s, 20, np.random.default_rng(0))
    assert np.array_equal(idx, idx2) and np.array_equal(y, y2)


def test_boundary_frac():
    s = toy_subject()
    b = boundary_mask(s.label, s.mask).reshape(-1)[s.mask_indices]
    idx, y = sample_voxels(s, 40, np.random.default_rng(1), boundary_frac=1.0)
    assert b[idx].all()
    idx, y = sample_voxels(s, 40, np.random.default_rng(1), boundary_frac=0.5)
    assert b[idx].mean() >= 0.5


def test_class_priors_and_adjust():
    s = toy_subject()
    pri = class_priors([s])
    assert pri.shape == (3,) and pri.sum() == pytest.approx(1.0)
    p = np.full((5, 3), 1 / 3, dtype=np.float32)
    adj = adjust_priors(p, np.full(3, 1 / 3), pri)
    assert np.allclose(adj, pri[None, :], atol=1e-6)
    assert np.allclose(adj.sum(1), 1.0)
