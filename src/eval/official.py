"""Scores officiels du serveur d'évaluation iSeg-2017, lus depuis le classeur du challenge.

C'est la seule source de vérité sur les 13 sujets de test : leur vérité terrain n'est pas
publique, et rien dans ce dépôt ne permet de recalculer ces chiffres. On les lit donc, on ne
les recopie pas.

DISTANCES. L'article du challenge décrit HD95. L'équivalence exacte avec notre
implémentation n'a pas été vérifiée. Un rapport entre agrégats de deux jeux différents
ne prouve pas que les définitions sont différentes et n'identifie pas la cause des erreurs.

Le classeur place ses données en K10:V26, avec un en-tête à deux niveaux : les tissus
(CSF, GM, WM) sur une ligne, les métriques (DICE, MHD, ASD) sur la suivante. On lit cet
en-tête au lieu de coder les colonnes en dur, pour qu'un classeur redéposé ailleurs dans la
feuille soit toujours lu correctement.
"""
from __future__ import annotations

import math
import statistics as st
from pathlib import Path

TISSUES = ("csf", "gm", "wm")
METRICS = ("dice", "mhd", "asd")
FR = {"csf": "LCR", "gm": "SG", "wm": "SB"}
XLSX_NAME = "evaluation_result_iseg2017_results.xlsx"


def _locate(ws) -> tuple[int, dict[tuple[str, str], int]]:
    """(ligne du premier sujet, {(tissu, métrique) -> index de colonne}) lus sur l'en-tête."""
    header_row = None
    for row in ws.iter_rows():
        for cell in row:
            if isinstance(cell.value, str) and cell.value.strip().upper() == "ID":
                header_row, id_col = cell.row, cell.column
                break
        if header_row:
            break
    if header_row is None:
        raise ValueError("colonne « ID » introuvable dans le classeur")

    # Les métriques vont par groupes de trois — DICE, MHD, ASD — et le nom du tissu est
    # écrit au-dessus du groupe, pas nécessairement au-dessus de sa première colonne : dans
    # le classeur reçu il est centré sur la colonne du milieu. On délimite donc les groupes
    # sur la ligne des métriques, puis on cherche le tissu n'importe où au-dessus du groupe.
    groups: list[list[int]] = []
    for col in range(id_col + 1, ws.max_column + 1):
        metric = ws.cell(header_row, col).value
        metric = metric.strip().lower() if isinstance(metric, str) else None
        if metric == METRICS[0]:
            groups.append([col])
        elif metric in METRICS and groups and len(groups[-1]) < len(METRICS):
            groups[-1].append(col)

    cols: dict[tuple[str, str], int] = {}
    for group in groups:
        if len(group) != len(METRICS):
            continue
        tissue = next((v.strip().lower()
                       for c in range(group[0], group[-1] + 1)
                       if isinstance(v := ws.cell(header_row - 1, c).value, str)
                       and v.strip().lower() in TISSUES), None)
        if tissue is None:
            continue
        for metric, col in zip(METRICS, group):
            cols[(tissue, metric)] = col

    manquantes = [(t, m) for t in TISSUES for m in METRICS if (t, m) not in cols]
    if manquantes:
        raise ValueError(f"colonnes absentes du classeur : {manquantes}")
    return header_row + 1, cols | {("id", "id"): id_col}


def load_official_scores(path: Path) -> dict:
    """{per_subject: {id: {dice_csf, mhd_csf, ...}}, mean: {...}, std: {...}, dice_mean: float}."""
    import openpyxl  # import local : le reste du dépôt tourne sans openpyxl

    ws = openpyxl.load_workbook(path, data_only=True)["Sheet1"]
    first_row, cols = _locate(ws)
    id_col = cols[("id", "id")]

    per_subject: dict[int, dict[str, float]] = {}
    for row in range(first_row, ws.max_row + 1):
        raw = ws.cell(row, id_col).value
        if raw is None or not str(raw).strip().isdigit():
            continue  # les lignes « Mean » et « Std » du classeur, que nous recalculons
        vals = {f"{m}_{t}": float(ws.cell(row, cols[(t, m)]).value)
                for t in TISSUES for m in METRICS}
        vals["dice_mean"] = st.mean(vals[f"dice_{t}"] for t in TISSUES)
        per_subject[int(raw)] = vals

    if not per_subject:
        raise ValueError("aucun sujet lu dans le classeur")
    keys = list(next(iter(per_subject.values())))
    col = lambda k: [per_subject[s][k] for s in sorted(per_subject)]  # noqa: E731
    return {
        "source": path.name,
        "subjects": sorted(per_subject),
        "per_subject": per_subject,
        "mean": {k: st.mean(col(k)) for k in keys},
        "std": {k: st.stdev(col(k)) for k in keys},
        "dice_mean": st.mean(col("dice_mean")),
        "best_subject": max(per_subject, key=lambda s: per_subject[s]["dice_mean"]),
        "worst_subject": min(per_subject, key=lambda s: per_subject[s]["dice_mean"]),
    }


def mhd_ratio_to_loo(scores: dict, loo_mean: dict[str, float]) -> dict[str, float]:
    """Rapport descriptif entre deux populations, sans conclusion sur les définitions."""
    return {t: scores["mean"][f"mhd_{t}"] / loo_mean[f"mhd_{t}"] for t in TISSUES}
