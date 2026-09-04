import numpy as np

from src.features.normalize import apply_stats, subject_stats
from src.features.registry import build_extractor
from tests.test_sampling import toy_subject


def test_subject_stats_are_computed_on_the_subject_itself(tmp_path):
    s = toy_subject()
    ext = build_extractor(["intensity"], cache_dir=tmp_path, verbose=False)
    mean, std = subject_stats(ext, s, cache_dir=tmp_path)
    X = np.asarray(ext.transform(s))
    assert np.allclose(mean, X.mean(0), atol=1e-5)
    assert np.allclose(std, X.std(0), atol=1e-4)
    # standardisation : moyenne nulle, écart-type unité sur le sujet lui-même.
    # Une colonne constante (ici t1 == t2) a un écart-type nul et reste à zéro : c'est voulu,
    # l'epsilon du dénominateur évite la division par zéro.
    Z = apply_stats(X, (mean, std))
    varying = X.std(0) > 1e-6
    assert np.abs(Z.mean(0)).max() < 1e-4
    assert np.abs(Z[:, varying].std(0) - 1).max() < 1e-3
    assert np.abs(Z[:, ~varying]).max() == 0.0


def test_stats_are_cached_and_reused(tmp_path):
    s = toy_subject()
    ext = build_extractor(["intensity"], cache_dir=tmp_path, verbose=False)
    a = subject_stats(ext, s, cache_dir=tmp_path)
    assert list(tmp_path.glob("subject-99/stats-*.npz"))
    b = subject_stats(ext, s, cache_dir=tmp_path)
    assert np.array_equal(a[0], b[0]) and np.array_equal(a[1], b[1])


def test_apply_stats_without_stats_is_identity():
    X = np.arange(6, dtype=np.float32).reshape(3, 2)
    assert np.array_equal(apply_stats(X, None), X)
