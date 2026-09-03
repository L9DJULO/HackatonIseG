from pathlib import Path

import numpy as np
import pytest

from src.io import load_subject, mask_agreement, mask_to_volume, remap_labels

DATA = Path(__file__).resolve().parents[1] / "data"
pytestmark = pytest.mark.skipif(not (DATA / "train").exists(), reason="données absentes")


def test_remap_labels():
    raw = np.array([[0, 10], [150, 250]], dtype=np.uint8)
    assert remap_labels(raw).tolist() == [[0, 1], [2, 3]]
    with pytest.raises(ValueError):
        remap_labels(np.array([0, 7], dtype=np.uint8))


def test_load_subject_train():
    s = load_subject(1, DATA)
    assert s.t1.shape == (144, 192, 256) and s.t1.dtype == np.float32
    assert s.t2.shape == s.t1.shape
    assert s.label is not None and s.label.dtype == np.uint8 and set(np.unique(s.label)) == {0, 1, 2, 3}
    assert s.mask.dtype == bool and s.spacing == (1.0, 1.0, 1.0)
    assert mask_agreement(s) == 1.0
    assert s.mask_labels.min() == 1 and s.mask_labels.shape == (s.mask.sum(),)


def test_load_subject_test_has_no_label():
    s = load_subject(11, DATA)
    assert s.label is None and s.mask.sum() > 0


def test_mask_to_volume_roundtrip():
    mask = np.zeros((4, 5, 6), dtype=bool)
    mask[1:3, 2:4, :] = True
    v = np.arange(mask.sum(), dtype=np.float32)
    vol = mask_to_volume(v, mask)
    assert vol.shape == mask.shape
    assert np.array_equal(vol.reshape(-1)[np.flatnonzero(mask)], v)
    vol2 = mask_to_volume(np.stack([v, v], 1), mask)
    assert vol2.shape == mask.shape + (2,)
