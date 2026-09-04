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
