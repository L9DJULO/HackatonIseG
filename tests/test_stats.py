import numpy as np

from src.eval.stats import cliff_delta, compare, format_table


def fake_run(name, values, metric="dice_mean"):
    return {"run_name": name, "per_subject": {str(i + 1): {metric: v} for i, v in enumerate(values)}}


def test_cliff_delta():
    assert cliff_delta(np.array([1.0, 1.0, 1.0])) == 1.0
    assert cliff_delta(np.array([-1.0, -1.0])) == -1.0
    assert cliff_delta(np.array([1.0, -1.0])) == 0.0


def test_consistent_improvement_is_distinguishable():
    base = np.linspace(0.70, 0.79, 10)
    a, b = fake_run("a", base), fake_run("b", base + 0.02)
    c = compare(a, b)
    assert c.n_improved == 10 and c.n_subjects == 10
    assert c.delta > 0 and c.p_value < 0.05
    assert c.cliff_delta == 1.0 and c.verdict.startswith("distinguable")


def test_noisy_difference_is_not_distinguishable():
    rng = np.random.default_rng(0)
    base = rng.normal(0.8, 0.02, 10)
    noise = rng.normal(0, 0.02, 10)
    c = compare(fake_run("a", base), fake_run("b", base + noise))
    assert c.verdict.startswith("NON")


def test_identical_runs_give_zero_delta():
    base = np.linspace(0.7, 0.8, 10)
    c = compare(fake_run("a", base), fake_run("b", base))
    assert c.delta == 0.0 and c.p_value == 1.0 and c.n_improved == 0
    assert c.verdict.startswith("NON")


def test_format_table_has_one_row_per_comparison():
    base = np.linspace(0.7, 0.8, 10)
    cs = [compare(fake_run("a", base), fake_run("b", base + 0.01))]
    table = format_table(cs)
    assert table.count("\n") == 2 and "a → b" in table


# --- correction de multiplicité -----------------------------------------------------------

import numpy as np  # noqa: E402
import pytest  # noqa: E402

from src.eval.stats import Comparison, apply_holm, holm  # noqa: E402


def test_holm_cas_connus():
    assert holm([]).size == 0
    assert holm([0.03]) == pytest.approx([0.03])
    # Bonferroni sur la plus petite, puis décroissance du multiplicateur
    assert holm([0.01, 0.02, 0.03]) == pytest.approx([0.03, 0.04, 0.04])


def test_holm_est_monotone_et_borne():
    rng = np.random.default_rng(0)
    p = rng.random(20)
    a = holm(p)
    assert (a <= 1.0).all() and (a >= p - 1e-12).all(), "une p ajustée ne descend jamais sous la brute"
    ordre = np.argsort(p)
    assert (np.diff(a[ordre]) >= -1e-12).all(), "l'ajustement doit rester monotone"


def _comp(p, n_improved=10):
    return Comparison(
        name_a="a", name_b="b", metric="dice_mean", mean_a=0.8, mean_b=0.81, delta=0.01,
        delta_std=0.002, n_improved=n_improved, n_subjects=10, p_value=p, p_holm=p,
        cohen_d=1.0, cliff_delta=1.0, verdict="",
    )


def test_apply_holm_refait_les_verdicts():
    famille = [_comp(0.002), _comp(0.010), _comp(0.625)]
    apply_holm(famille)
    assert famille[0].p_holm == pytest.approx(0.006) and famille[0].verdict == "distinguable du bruit"
    assert famille[2].verdict == "NON distinguable du bruit"


def test_apply_holm_peut_retirer_un_verdict():
    """Le cas qui compte, sur la famille réelle du rapport : un résultat significatif en brut
    ne l'est plus une fois replacé parmi les neuf comparaisons déclarées."""
    brutes = [0.002, 0.002, 0.625, 0.064, 0.695, 0.064, 0.010, 0.002, 0.002]
    famille = [_comp(p) for p in brutes]
    apply_holm(famille)
    ajustees = [round(c.p_holm, 3) for c in famille]
    assert ajustees == [0.018, 0.018, 1.0, 0.256, 1.0, 0.256, 0.050, 0.018, 0.018]
    quatre_positifs = [famille[i] for i in (0, 1, 7, 8)]
    assert all(c.verdict == "distinguable du bruit" for c in quatre_positifs), "les gains réels survivent"
    assert famille[6].verdict == "NON distinguable du bruit", "à p ajusté = 0.050 pile, on ne conclut pas"


def test_une_degradation_systematique_reste_un_resultat():
    """1/10 sujets améliorés, c'est 9/10 dégradés : un effet net, dans l'autre sens.

    Le verdict est symétrique. Confondre « effet négatif » et « pas d'effet » ferait passer
    une dégradation systématique pour du bruit.
    """
    famille = [_comp(0.004, n_improved=1)]
    apply_holm(famille)
    assert famille[0].verdict == "distinguable du bruit"


def test_apply_holm_exige_un_nombre_minimal_de_sujets_dans_le_meme_sens():
    famille = [_comp(0.002, n_improved=5)]
    apply_holm(famille)
    assert famille[0].verdict == "NON distinguable du bruit", "5/10 sujets : pas un effet systématique"


def test_sens_de_la_metrique():
    """Pour une distance, « amélioré » veut dire « qui diminue »."""
    from src.eval.stats import lower_is_better

    assert lower_is_better("asd_gm") and lower_is_better("mhd_csf")
    assert not lower_is_better("dice_mean")

    def run(name, vals):
        return {"run_name": name, "per_subject": {str(i): {"asd_gm": v} for i, v in enumerate(vals)}}

    a = run("a", [1.0] * 10)
    b = run("b", [0.5] * 10)  # distances divisées par deux : les 10 sujets s'améliorent
    c = compare(a, b, metric="asd_gm")
    assert c.delta < 0
    assert c.n_improved == 10, "une distance qui baisse est une amélioration"
    assert c.cliff_delta > 0
