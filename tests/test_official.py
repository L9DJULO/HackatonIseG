"""Le classeur du serveur iSeg-2017 est la seule source des chiffres de test.

Rien dans ce dépôt ne permet de les recalculer : la vérité terrain des 13 sujets n'est pas
publique. Le seul contrôle possible est donc de vérifier qu'on le lit correctement — que les
colonnes sont bien appariées à leur tissu, et que nos agrégats retombent sur les lignes
« Mean » et « Std » que le classeur calcule lui-même.
"""
import math
from pathlib import Path

import pytest

from src.eval.official import (
    METRICS, TISSUES, XLSX_NAME, load_official_scores, mhd_ratio_to_loo,
)

ROOT = Path(__file__).resolve().parents[1]
XLSX = ROOT / "results" / XLSX_NAME
pytestmark = pytest.mark.skipif(not XLSX.exists(), reason="classeur du serveur absent")


@pytest.fixture(scope="module")
def scores():
    return load_official_scores(XLSX)


def test_les_treize_sujets_de_test(scores):
    assert scores["subjects"] == list(range(11, 24))


def test_nos_agregats_retombent_sur_ceux_du_classeur(scores):
    """Le classeur porte ses propres lignes Mean et Std : on les recalcule et on compare.

    C'est le contrôle qui attrape une colonne mal appariée à son tissu — l'en-tête place le
    nom du tissu au-dessus de la colonne du MILIEU de son groupe, pas de la première.
    """
    import openpyxl
    ws = openpyxl.load_workbook(XLSX, data_only=True)["Sheet1"]
    attendu = {}
    for row in ws.iter_rows():
        label = row[0].value if row else None
        for cell in row:
            if isinstance(cell.value, str) and cell.value.strip() in ("Mean", "Std"):
                label = cell.value.strip()
                attendu[label] = cell.row
    assert set(attendu) == {"Mean", "Std"}, "lignes Mean/Std introuvables"

    # on relit les valeurs du classeur par la même carte de colonnes que le parseur
    from src.eval.official import _locate
    _, cols = _locate(ws)
    for t in TISSUES:
        for m in METRICS:
            col = cols[(t, m)]
            assert scores["mean"][f"{m}_{t}"] == pytest.approx(
                float(ws.cell(attendu["Mean"], col).value), abs=1e-9)
            assert scores["std"][f"{m}_{t}"] == pytest.approx(
                float(ws.cell(attendu["Std"], col).value), abs=1e-9)


def test_dice_moyen_et_extremes(scores):
    assert scores["dice_mean"] == pytest.approx(0.844512, abs=5e-7)
    assert (scores["best_subject"], scores["worst_subject"]) == (13, 20)


def test_agregats_par_tissu_sur_une_ligne_connue(scores):
    # Lecture indépendante de la ligne du sujet 11 : évite de valider un appariement
    # de colonnes erroné en réutilisant la carte de colonnes du parseur.
    import openpyxl
    ws = openpyxl.load_workbook(XLSX, data_only=True)["Sheet1"]
    rows = list(ws.iter_rows(values_only=True))
    row = next(r for r in rows if len(r) >= 22 and str(r[10]).strip() == "11")
    for tissue, start in (("csf", 11), ("gm", 15), ("wm", 19)):
        for metric, offset in (("dice", 0), ("mhd", 1), ("asd", 2)):
            assert scores["per_subject"][11][f"{metric}_{tissue}"] == float(row[start+offset])
