import numpy as np
import pytest
from sklearn.linear_model import LogisticRegression

from src.models.params import check_agreement, count_linear, count_mlp, count_sklearn
from src.models.stub import LogRegStub, RandomStub


def test_count_linear_conventions():
    assert count_linear(151) == 3 * 152 == 456
    assert count_linear(151, redundant=False) == 2 * 152


def test_convention_inverse_du_rapport():
    """Le rapport (§ 3.5) donne 456 et 758 comme deux décomptes EXACTS de la même
    configuration, sous les deux conventions possibles pour le scaler intra-sujet.
    L'argument en ordres de grandeur repose sur le fait que ces deux nombres tombent dans
    la même tranche ; il tombe si l'un des deux est faux. On les recompte donc ici.
    """
    F = 151
    compte, compte_inverse = count_linear(F), count_linear(F) + 2 * F
    assert (compte, compte_inverse) == (456, 758)
    assert int(np.floor(np.log10(compte))) == int(np.floor(np.log10(compte_inverse))) == 2


def test_count_mlp():
    # 10 -> 4 -> 3 : (10*4+4) + (4*3+3) = 44 + 15
    assert count_mlp(10, [4]) == 59
    assert count_mlp(10, [4, 5]) == (10 * 4 + 4) + (4 * 5 + 5) + (5 * 3 + 3)


def _fit_stub(n_features=7, n=300, seed=0):
    rng = np.random.default_rng(seed)
    X = rng.normal(size=(n, n_features)).astype(np.float32)
    y = rng.choice([1, 2, 3], size=n).astype(np.uint8)
    return LogRegStub().fit(X, y), n_features


def test_stub_has_no_scaler_and_matches_convention():
    model, F = _fit_stub()
    assert model.param_breakdown() == {"weights": 3 * F, "bias": 3}
    assert model.n_params() == count_linear(F)
    assert not hasattr(model, "scaler")


def test_check_agreement_detects_mismatch():
    model, F = _fit_stub()
    assert count_sklearn(model.clf) == model.n_params()
    check_agreement(model.n_params(), model.clf)
    with pytest.raises(ValueError):
        check_agreement(model.n_params() - 10, model.clf)


def test_random_stub_has_no_params():
    m = RandomStub()
    assert m.n_params() == 0 and m.param_breakdown() == {}
    p = m.predict_proba(np.zeros((5, 3), dtype=np.float32))
    assert p.shape == (5, 3) and np.allclose(p.sum(1), 1.0)
