"""Comparaisons statistiques appariées entre configurations.

Dix sujets seulement : un écart de quelques millièmes de Dice peut être du bruit. Le même sujet
passant dans toutes les configurations, les comparaisons sont APPARIÉES. On rapporte pour chaque
comparaison :
  - le delta moyen de Dice et son écart-type inter-sujets ;
  - le test des rangs signés de Wilcoxon apparié (bilatéral). Avec n = 10, la plus petite
    p-valeur atteignable est 0.002 ; aucune correction de multiplicité n'est appliquée, les
    comparaisons sont déclarées à l'avance et peu nombreuses ;
  - la taille d'effet : d de Cohen apparié (delta moyen / écart-type des deltas) et le
    delta de Cliff, non paramétrique ;
  - le nombre de sujets améliorés sur 10. Un gain porté par un seul sujet n'est pas un gain.

Seuil de lecture retenu : une différence est déclarée NON DISTINGUABLE DU BRUIT si p >= 0.05 ou
si moins de 8 sujets sur 10 vont dans le même sens.
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


def compare(run_a: dict, run_b: dict, metric: str = "dice_mean") -> Comparison:
    """Compare b à a sur les sujets communs. Un delta positif signifie que b fait mieux que a."""
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
    n_up = int((d > 0).sum())
    distinguable = p < 0.05 and (n_up >= 8 or n_up <= 2)
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
        cohen_d=float(d.mean() / sd) if sd > 0 else 0.0,
        cliff_delta=cliff_delta(d),
        verdict="distinguable du bruit" if distinguable else "NON distinguable du bruit",
    )


def format_table(comparisons: list[Comparison]) -> str:
    head = (
        "| comparaison | métrique | Dice A | Dice B | Δ | écart-type Δ | sujets améliorés | p (Wilcoxon) | d de Cohen | δ de Cliff | verdict |\n"
        "|---|---|---:|---:|---:|---:|:---:|---:|---:|---:|---|\n"
    )
    rows = []
    for c in comparisons:
        rows.append(
            f"| {c.name_a} → {c.name_b} | {c.metric.replace('dice_', '')} | {c.mean_a:.4f} | {c.mean_b:.4f} | "
            f"{c.delta:+.4f} | {c.delta_std:.4f} | {c.n_improved}/{c.n_subjects} | {c.p_value:.3f} | "
            f"{c.cohen_d:+.2f} | {c.cliff_delta:+.2f} | {c.verdict} |"
        )
    return head + "\n".join(rows)
