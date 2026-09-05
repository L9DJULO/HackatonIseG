"""Comparaisons statistiques appariées entre configurations.

Dix sujets seulement : un écart de quelques millièmes de Dice peut être du bruit. Le même sujet
passant dans toutes les configurations, les comparaisons sont APPARIÉES. On rapporte pour chaque
comparaison :
  - le delta moyen de Dice et son écart-type inter-sujets ;
  - le test des rangs signés de Wilcoxon apparié (bilatéral). Avec n = 10, la plus petite
    p-valeur atteignable est 0.002 ;
  - la p-valeur CORRIGÉE DE LA MULTIPLICITÉ par la méthode de Holm, sur la famille entière des
    comparaisons déclarées à l'avance. Les comparaisons sont peu nombreuses et pré-déclarées,
    ce qui rendrait la correction discutablement facultative ; on l'applique quand même, parce
    qu'elle ne coûte rien à produire et qu'elle retire au lecteur une objection légitime. Le
    verdict est rendu sur la p-valeur AJUSTÉE, jamais sur la brute ;
  - la taille d'effet : d de Cohen apparié (delta moyen / écart-type des deltas) et le
    delta de Cliff, non paramétrique ;
  - le nombre de sujets améliorés sur 10. Un gain porté par un seul sujet n'est pas un gain.

Seuil de lecture retenu : une différence est déclarée NON DISTINGUABLE DU BRUIT si la p-valeur
AJUSTÉE est >= 0.05, ou si moins de 8 sujets sur 10 vont dans le même sens. Tant qu'une
comparaison n'a pas été replacée dans sa famille par `apply_holm`, sa p-valeur ajustée vaut sa
p-valeur brute et son verdict est provisoire.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, asdict
from pathlib import Path

import numpy as np
from scipy import stats as sps


@dataclass
class Comparison:
    name_a: str
    name_b: str
    metric: str
    mean_a: float
    mean_b: float
    delta: float
    delta_std: float
    n_improved: int
    n_subjects: int
    p_value: float
    p_holm: float
    cohen_d: float
    cliff_delta: float
    verdict: str

    def as_dict(self) -> dict:
        return asdict(self)


def load_run(path: Path) -> dict:
    return json.loads(Path(path).read_text())


def per_subject_values(run: dict, metric: str = "dice_mean") -> dict[str, float]:
    return {sid: m[metric] for sid, m in run["per_subject"].items()}


def cliff_delta(deltas: np.ndarray) -> float:
    """Delta de Cliff d'un échantillon apparié : P(delta > 0) - P(delta < 0)."""
    return float((np.sum(deltas > 0) - np.sum(deltas < 0)) / deltas.size)


def lower_is_better(metric: str) -> bool:
    """Le Dice se maximise ; les distances de surface (ASD, MHD) se minimisent.

    Sans cette distinction, « sujets améliorés » compterait les sujets dont la DISTANCE
    augmente, c'est-à-dire exactement l'inverse de ce que la colonne annonce.
    """
    return metric.startswith(("asd", "mhd", "hausdorff"))


def compare(run_a: dict, run_b: dict, metric: str = "dice_mean") -> Comparison:
    """Compare b à a sur les sujets communs. Le delta est toujours b - a, dans l'unité de la
    métrique ; « amélioré » tient compte du sens de la métrique (voir lower_is_better)."""
    a, b = per_subject_values(run_a, metric), per_subject_values(run_b, metric)
    subjects = sorted(set(a) & set(b), key=int)
    va = np.array([a[s] for s in subjects])
    vb = np.array([b[s] for s in subjects])
    d = vb - va
    if np.allclose(d, 0):
        p = 1.0
    else:
        p = float(sps.wilcoxon(vb, va, zero_method="wilcox").pvalue)
    sd = float(d.std(ddof=1)) if d.size > 1 else 0.0
    better = d < 0 if lower_is_better(metric) else d > 0
    n_up = int(better.sum())
    distinguable = p < 0.05 and (n_up >= 8 or n_up <= 2)  # provisoire : voir apply_holm
    return Comparison(
        name_a=run_a["run_name"],
        name_b=run_b["run_name"],
        metric=metric,
        mean_a=float(va.mean()),
        mean_b=float(vb.mean()),
        delta=float(d.mean()),
        delta_std=sd,
        n_improved=n_up,
        n_subjects=len(subjects),
        p_value=p,
        p_holm=p,
        cohen_d=float(d.mean() / sd) if sd > 0 else 0.0,
        cliff_delta=cliff_delta(-d if lower_is_better(metric) else d),
        verdict="distinguable du bruit" if distinguable else "NON distinguable du bruit",
    )


def holm(p_values) -> np.ndarray:
    """Correction de Holm-Bonferroni, monotone. Rend les p-valeurs ajustées, dans l'ordre reçu.

    Procédure descendante : la i-ème plus petite p-valeur d'une famille de m est multipliée par
    (m - i), et l'on impose la monotonie en propageant le maximum courant. Plus puissante que
    Bonferroni, et sans hypothèse sur la dépendance entre les tests — ce qui compte ici, où les
    comparaisons partagent leurs sujets et sont donc fortement corrélées.
    """
    p = np.asarray(p_values, dtype=float)
    m = p.size
    if m == 0:
        return p
    order = np.argsort(p, kind="stable")
    adjusted = np.empty(m, dtype=float)
    running = 0.0
    for rank, i in enumerate(order):
        running = max(running, min(1.0, (m - rank) * p[i]))
        adjusted[i] = running
    return adjusted


def apply_holm(comparisons: list[Comparison]) -> list[Comparison]:
    """Replace chaque comparaison dans sa famille : remplit p_holm et refait les verdicts.

    À appeler UNE FOIS sur la famille complète des comparaisons déclarées à l'avance. Appeler
    sur un sous-ensemble donnerait une correction plus faible que la vérité, donc plus
    permissive : c'est l'erreur à ne pas commettre.
    """
    if not comparisons:
        return comparisons
    adj = holm([c.p_value for c in comparisons])
    for c, a in zip(comparisons, adj):
        c.p_holm = float(a)
        c.verdict = (
            "distinguable du bruit"
            if a < 0.05 and (c.n_improved >= 8 or c.n_improved <= c.n_subjects - 8)
            else "NON distinguable du bruit"
        )
    return comparisons


def format_table(comparisons: list[Comparison]) -> str:
    head = (
        "| comparaison | métrique | A | B | Δ | écart-type Δ | sujets améliorés | p brut | p ajusté (Holm) | d de Cohen | δ de Cliff | verdict |\n"
        "|---|---|---:|---:|---:|---:|:---:|---:|---:|---:|---:|---|\n"
    )
    rows = []
    for c in comparisons:
        rows.append(
            f"| {c.name_a} → {c.name_b} | {c.metric.replace('dice_', '')} | {c.mean_a:.4f} | {c.mean_b:.4f} | "
            f"{c.delta:+.4f} | {c.delta_std:.4f} | {c.n_improved}/{c.n_subjects} | {c.p_value:.3f} | "
            f"{c.p_holm:.3f} | {c.cohen_d:+.2f} | {c.cliff_delta:+.2f} | {c.verdict} |"
        )
    return head + "\n".join(rows)
