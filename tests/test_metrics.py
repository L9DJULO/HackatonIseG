import numpy as np
import pytest

from src.eval.metrics import asd, dice, evaluate_subject, hausdorff, mhd, surface_distances


def cube(shape=(20, 20, 20), lo=5, hi=15, shift=(0, 0, 0)):
    m = np.zeros(shape, dtype=bool)
    s = [slice(lo + d, hi + d) for d in shift]
    m[tuple(s)] = True
    return m


def test_identical_cube():
    a = cube()
    assert dice(a, a) == 1.0
    assert asd(a, a) == 0.0
    assert hausdorff(a, a) == 0.0
    assert mhd(a, a) == 0.0


def test_cube_shifted_one_voxel():
    a = cube()
    b = cube(shift=(1, 0, 0))
    s = 10  # côté du cube
    # Dice analytique : recouvrement s^2 (s-1), total 2 s^3
    assert dice(a, b) == pytest.approx((s - 1) / s)
    # Hausdorff exact = 1 voxel
    assert hausdorff(a, b) == 1.0
    # ASD : seule la face x=lo de a (s^2 voxels) est à distance 1 de b, idem face x=hi de b.
    d1, d2 = surface_distances(a, b)
    n_surf = 6 * s * s - 12 * s + 8  # voxels de surface d'un cube plein de côté s
    assert d1.size == n_surf and d2.size == n_surf
    assert d1.sum() == pytest.approx(s * s) and d2.sum() == pytest.approx(s * s)
    assert asd(a, b) == pytest.approx(2 * s * s / (2 * n_surf))
    assert mhd(a, b, mode="dubuisson") == pytest.approx(s * s / n_surf)


def test_spacing_scales_distances():
    a = cube()
    b = cube(shift=(1, 0, 0))
    assert hausdorff(a, b, spacing=(2.0, 1.0, 1.0)) == 2.0
    assert hausdorff(a, b, spacing=(1.0, 3.0, 1.0)) == 1.0


def test_two_spheres_offset():
    z, y, x = np.mgrid[:40, :40, :40]
    a = (x - 20) ** 2 + (y - 20) ** 2 + (z - 20) ** 2 <= 100
    b = (x - 21) ** 2 + (y - 20) ** 2 + (z - 20) ** 2 <= 100
    assert 0.9 < dice(a, b) < 1.0
    assert hausdorff(a, b) == pytest.approx(1.0)
    assert 0.0 < asd(a, b) < 1.0


def test_disjoint_and_empty():
    a = cube(lo=1, hi=4)
    b = cube(lo=10, hi=14)
    assert dice(a, b) == 0.0
    # coin (13,13,13) de b vers coin (3,3,3) de a : sqrt(3 * 10^2)
    assert hausdorff(a, b) == pytest.approx(np.sqrt(300.0))
    empty = np.zeros_like(a)
    assert dice(empty, empty) == 1.0
    assert dice(a, empty) == 0.0
    assert np.isinf(asd(a, empty))


def test_evaluate_subject_keys_and_background_ignored():
    gt = np.zeros((16, 16, 16), dtype=np.uint8)
    gt[2:6] = 1
    gt[6:10] = 2
    gt[10:14] = 3
    pred = gt.copy()
    pred[0:2] = 3  # erreur dans le fond : compte contre WM, pas comme classe "fond"
    m = evaluate_subject(pred, gt)
    assert set(m) >= {"dice_csf", "dice_gm", "dice_wm", "asd_csf", "mhd_wm", "dice_mean"}
    assert m["dice_csf"] == 1.0 and m["dice_gm"] == 1.0 and m["dice_wm"] < 1.0
    assert m["dice_mean"] == pytest.approx((1 + 1 + m["dice_wm"]) / 3)
