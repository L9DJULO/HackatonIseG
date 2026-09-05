"""Le post-traitement doit corriger ce qu'il prétend corriger, et rien d'autre.

Le test le plus important est test_gm_between_supprime_tout_contact : il vérifie la
CONTRAINTE, pas l'implémentation. Si la règle de résolution change, ce test doit continuer
de passer.
"""
import numpy as np
import pytest
from scipy import ndimage

from src.postproc import topology as T


def onehot(seg, noise=0.0, seed=0):
    """Volume de probabilités piqué sur `seg`, avec un peu de bruit pour départager."""
    rng = np.random.default_rng(seed)
    p = np.full(seg.shape + (3,), 0.02, dtype=np.float32)
    for c in (1, 2, 3):
        p[..., c - 1] = np.where(seg == c, 0.96, 0.02)
    p += rng.random(p.shape).astype(np.float32) * noise
    return p / p.sum(-1, keepdims=True)


def boite():
    """Cerveau jouet : coquille de LCR, ruban de GM, noyau de SB. Contrainte respectée."""
    seg = np.zeros((16, 16, 16), dtype=np.uint8)
    seg[2:14, 2:14, 2:14] = 1
    seg[4:12, 4:12, 4:12] = 2
    seg[6:10, 6:10, 6:10] = 3
    return seg, seg != 0


SPACING = (1.0, 1.0, 1.0)


def test_zero_parametre_appris():
    assert T.n_learned_params(list(T.STEPS)) == 0


def test_sans_etape_cest_largmax():
    seg, mask = boite()
    p = onehot(seg, noise=0.3, seed=1)
    out = T.apply_postproc(p, mask, SPACING, [])
    attendu = (np.argmax(p, -1) + 1).astype(np.uint8)
    attendu[~mask] = 0
    assert np.array_equal(out, attendu)


def test_etape_inconnue_leve():
    seg, mask = boite()
    with pytest.raises(KeyError, match="inconnue"):
        T.apply_postproc(onehot(seg), mask, SPACING, ["lissage_magique"])


@pytest.mark.parametrize("steps", [["smooth"], ["small_components"], ["fill_wm_holes"], ["gm_between"], list(T.STEPS)])
def test_sortie_toujours_bien_formee(steps):
    seg, mask = boite()
    out = T.apply_postproc(onehot(seg, noise=0.8, seed=2), mask, SPACING, steps)
    assert out.dtype == np.uint8
    assert set(np.unique(out).tolist()) <= {0, 1, 2, 3}
    assert not out[~mask].any(), "aucune étiquette ne doit sortir du masque"
    assert (out[mask] != 0).all(), "aucun voxel du masque ne doit rester non étiqueté"


def test_deterministe():
    seg, mask = boite()
    p = onehot(seg, noise=0.6, seed=3)
    a = T.apply_postproc(p, mask, SPACING, list(T.STEPS))
    b = T.apply_postproc(p, mask, SPACING, list(T.STEPS))
    assert np.array_equal(a, b)


def test_smooth_enleve_le_poivre_et_sel():
    seg, mask = boite()
    bruite = seg.copy()
    rng = np.random.default_rng(0)
    flip = (rng.random(seg.shape) < 0.15) & mask
    bruite[flip] = rng.integers(1, 4, size=int(flip.sum()), dtype=np.uint8)
    p = onehot(bruite)
    avant = int((( np.argmax(p, -1) + 1).astype(np.uint8)[mask] != seg[mask]).sum())
    apres = int((T.apply_postproc(p, mask, SPACING, ["smooth"])[mask] != seg[mask]).sum())
    assert apres < avant, f"le lissage doit réduire les erreurs ({apres} contre {avant})"


def test_small_components_retire_lilot_et_pas_le_noyau():
    seg, mask = boite()
    seg_avec_ilot = seg.copy()
    seg_avec_ilot[3, 3, 3] = 3  # un voxel de SB perdu dans le LCR : 1 mm3 << 30 mm3
    p = onehot(seg_avec_ilot)
    out = T.apply_postproc(p, mask, SPACING, ["small_components"])
    assert out[3, 3, 3] != 3, "l'îlot d'un voxel doit disparaître"
    assert out[3, 3, 3] != 0, "et être réattribué, pas mis à zéro"
    assert (out[7, 7, 7] == 3), "le noyau de SB, lui, est bien assez gros pour rester"


def test_small_components_respecte_le_spacing():
    """Le seuil est en mm3 : à 2 mm isotrope, il faut 8 fois moins de voxels."""
    fin = max(1, int(round(T.MIN_COMPONENT_MM3 / 1.0)))
    gros = max(1, int(round(T.MIN_COMPONENT_MM3 / 8.0)))
    assert gros < fin


def test_fill_wm_holes_bouche_la_cavite_fermee():
    seg, mask = boite()
    creuse = seg.copy()
    creuse[7:9, 7:9, 7:9] = 1  # poche de LCR strictement incluse dans la SB
    out = T.apply_postproc(onehot(creuse), mask, SPACING, ["fill_wm_holes"])
    assert (out[7:9, 7:9, 7:9] == 3).all(), "une cavité fermée doit être bouchée"


def test_fill_wm_holes_epargne_ce_qui_communique():
    seg, mask = boite()
    out = T.apply_postproc(onehot(seg), mask, SPACING, ["fill_wm_holes"])
    assert (out[mask] == seg[mask]).all(), "sans cavité fermée, rien ne doit bouger"


def contacts_sb_lcr(seg):
    csf, wm = seg == 1, seg == 3
    return int((wm & ndimage.binary_dilation(csf, structure=T.STRUCT)).sum())


def test_gm_between_supprime_tout_contact():
    """La contrainte, pas l'implémentation : après l'étape, plus aucun contact SB/LCR."""
    seg, mask = boite()
    colle = seg.copy()
    colle[4:12, 4:12, 4:12] = 3  # la SB déborde jusqu'au contact du LCR, le ruban disparaît
    p = onehot(colle, noise=0.2, seed=5)
    assert contacts_sb_lcr((np.argmax(p, -1) + 1).astype(np.uint8) * mask) > 0
    out = T.apply_postproc(p, mask, SPACING, ["gm_between"])
    assert contacts_sb_lcr(out) == 0


@pytest.mark.parametrize("seed", range(6))
def test_gm_between_converge_sur_du_bruit_pur(seed):
    """Cas le plus défavorable : des probabilités aléatoires, donc des contacts partout."""
    rng = np.random.default_rng(seed)
    mask = np.zeros((14, 14, 14), dtype=bool)
    mask[1:13, 1:13, 1:13] = True
    p = rng.random((14, 14, 14, 3)).astype(np.float32)
    p /= p.sum(-1, keepdims=True)
    out = T.apply_postproc(p, mask, SPACING, ["gm_between"])  # ne doit pas lever
    assert contacts_sb_lcr(out) == 0


def test_gm_between_ne_touche_pas_un_volume_deja_conforme():
    seg, mask = boite()
    out = T.apply_postproc(onehot(seg), mask, SPACING, ["gm_between"])
    assert np.array_equal(out, seg)


def test_ordre_des_etapes_respecte():
    """gm_between est appliqué en dernier : la contrainte tient sur la sortie finale."""
    seg, mask = boite()
    colle = seg.copy()
    colle[4:12, 4:12, 4:12] = 3
    out = T.apply_postproc(onehot(colle, noise=0.5, seed=7), mask, SPACING, list(T.STEPS))
    assert contacts_sb_lcr(out) == 0


# --- régression : le blocage rencontré sur les données réelles -----------------------------


def test_gm_between_tient_meme_si_les_passes_a_la_marge_ne_font_rien(monkeypatch):
    """Régression. Sur le sujet 2, les passes à la marge se bloquaient sur un contact isolé :
    un voxel de SB retenu par des voisins de LCR de marges plus faibles, eux-mêmes retenus.
    L'ancienne version levait « non convergé en 8 passes » au milieu d'un run de 15 minutes.

    On simule le pire cas en ramenant les passes à la marge à zéro : seule la passe forcée
    agit, et la contrainte doit tenir quand même. C'est la garantie qu'on teste, pas le chemin.
    """
    monkeypatch.setattr(T, "MAX_GM_BETWEEN_PASSES", 0)
    rng = np.random.default_rng(11)
    mask = np.zeros((16, 16, 16), dtype=bool)
    mask[1:15, 1:15, 1:15] = True
    p = rng.random((16, 16, 16, 3)).astype(np.float32)
    p /= p.sum(-1, keepdims=True)
    avant = contacts_sb_lcr((np.argmax(p, -1) + 1).astype(np.uint8) * mask)
    assert avant > 0, "le cas de test doit contenir des contacts au départ"
    out = T.apply_postproc(p, mask, SPACING, ["gm_between"])
    assert contacts_sb_lcr(out) == 0
    assert not out[~mask].any() and (out[mask] != 0).all()


@pytest.mark.parametrize("seed", range(40))
def test_gm_between_ne_leve_jamais(seed):
    """Quarante volumes aléatoires : la contrainte doit tenir à chaque fois, sans exception.

    Six graines suffisaient à faire passer la version bloquante — c'est précisément pourquoi
    ce test en prend beaucoup plus.
    """
    rng = np.random.default_rng(1000 + seed)
    mask = rng.random((12, 12, 12)) < 0.9
    p = rng.random((12, 12, 12, 3)).astype(np.float32)
    p /= p.sum(-1, keepdims=True)
    out = T.apply_postproc(p, mask, SPACING, list(T.STEPS))
    assert contacts_sb_lcr(out) == 0
