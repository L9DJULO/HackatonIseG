"""Garantie anti-fuite : aucun bloc de features ne peut voir la vérité terrain.

C'est la propriété la plus critique du protocole. Si un bloc lisait `subject.label` ou une carte
de probabilité produite par un modèle entraîné, tous les chiffres de leave-one-out seraient
optimistes. Le test le vérifie mécaniquement plutôt que par lecture du code : on calcule les
features avec le vrai label, avec un label permuté, et sans label du tout, et on exige que les
trois sorties soient identiques bit à bit.
"""
import numpy as np
import pytest

from src.features.registry import BLOCKS, _load_blocks, build_block
from tests.test_sampling import toy_subject

_load_blocks()
ALL_BLOCKS = sorted(BLOCKS)


def test_registry_exposes_the_six_blocks():
    assert ALL_BLOCKS == ["context", "gaussian", "intensity", "morpho", "spatial", "symmetry"]


@pytest.mark.parametrize("name", ALL_BLOCKS)
def test_features_do_not_depend_on_the_label(name):
    block = build_block(name)
    s = toy_subject()
    reference = np.asarray(block.transform(s)).copy()

    # label entièrement permuté : les tissus changent d'étiquette, les images ne bougent pas
    s.label = np.where(s.mask, 4 - s.label, 0).astype(np.uint8)
    assert np.array_equal(np.asarray(block.transform(s)), reference)

    # aucun label du tout, comme sur les 13 sujets de test du challenge
    s.label = None
    assert np.array_equal(np.asarray(block.transform(s)), reference)


@pytest.mark.parametrize("name", ALL_BLOCKS)
def test_blocks_declare_zero_learned_parameters(name):
    assert build_block(name).n_learned_params == 0


def test_features_depend_only_on_the_current_subject():
    """Deux sujets traités dans un ordre différent donnent les mêmes features : pas d'état partagé."""
    a, b = toy_subject(seed=0), toy_subject(seed=1)
    b.t1 = b.t1 * 2 + 5
    b.subject_id = 100
    block = build_block("intensity")
    xa1, xb1 = np.asarray(block.transform(a)).copy(), np.asarray(block.transform(b)).copy()
    block2 = build_block("intensity")
    xb2, xa2 = np.asarray(block2.transform(b)).copy(), np.asarray(block2.transform(a)).copy()
    assert np.array_equal(xa1, xa2) and np.array_equal(xb1, xb2)
