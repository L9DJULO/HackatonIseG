"""Figure 5 : ablation en barres, avec les intervalles de confiance qui vont avec.

Deux panneaux, parce que les deux quantités ne se lisent pas de la même façon.

(a) Le Dice ABSOLU de chaque configuration, avec l'intervalle de confiance à 95 % de la
    moyenne sur les dix sujets. Ces intervalles se CHEVAUCHENT tous largement : lus seuls,
    ils donneraient à croire qu'aucune configuration ne se distingue.

(b) Le delta APPARIÉ par rapport à la configuration précédente, avec son propre intervalle de
    confiance. Le même sujet passant dans toutes les configurations, la variabilité
    inter-sujets — qui domine complètement le panneau (a) — s'annule dans la différence. Des
    intervalles disjoints de zéro apparaissent là où le panneau (a) ne montrait rien.

Le contraste entre les deux panneaux EST le message de la figure : sur dix sujets, comparer
des barres absolues ne prouve rien, et seule la comparaison appariée décide. C'est aussi ce
qui justifie le protocole statistique de la section 4.

L'axe du panneau (a) ne part pas de zéro, et la figure le dit : les écarts en jeu valent
quelques millièmes de Dice, un axe partant de zéro les rendrait tous invisibles.

Usage : python scripts/fig05_ablation.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from scipy import stats as sps

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.figstyle import ACCENT, NEUTRAL_EDGE, NEUTRAL_FILL, NEUTRAL_TEXT, use  # noqa: E402
from src.eval.stats import apply_holm, compare  # noqa: E402

RESULTS = ROOT / "results"
OUT = ROOT / "report" / "assets" / "fig05_ablation.pdf"

# (clé, étiquette courte, clé de la configuration de référence pour le delta apparié)
STEPS = [
    ("logreg_ABC", "A+B+C\nsans morphologie", None),
    ("logreg_ABCD_p0", "+ max-tree\net min-tree", "logreg_ABC"),
    ("logreg_ABCD_p1", "+ remontée\nde branche", "logreg_ABCD_p0"),
    ("logreg_ABCD_p2", "arbre des formes\nau lieu des deux", "logreg_ABCD_p1"),
    ("logreg_ABCD_p3", "+ filtres\nde grain", "logreg_ABCD_p2"),
    ("logreg_final", "+ symétrie\net contexte", "logreg_ABCD_p2"),
    ("logreg_final_smooth", "+ lissage et\nnettoyage", "logreg_final"),
    ("logreg_final_postproc", "+ contrainte\ntopologique", "logreg_final_smooth"),
    ("autocontext_final", "+ auto-contexte\nà deux étages", "logreg_final"),
    ("select_k40", "sélection K=40\n(456 -> 163 param.)", "logreg_final"),
]
CONF = 0.95


def load(name: str) -> dict | None:
    p = RESULTS / f"{name}.json"
    return json.loads(p.read_text()) if p.exists() else None


def declared_verdicts() -> dict[tuple[str, str], bool]:
    """Verdicts du protocole DÉCLARÉ : Wilcoxon apparié corrigé de Holm sur la famille entière.

    La figure ne décide pas par elle-même : un intervalle de confiance de Student suppose la
    normalité des deltas, le protocole de la section 4 ne la suppose pas, et les deux peuvent
    diverger sur dix sujets. C'est le protocole déclaré qui tranche — la figure ne fait que le
    montrer. Colorer selon l'intervalle affirmerait des significativités que le rapport ne
    revendique pas.
    """
    from scripts.report_assets import COMPARISONS  # famille déclarée, source unique

    pairs, comps = [], []
    for a, b, _ in COMPARISONS:
        ra, rb = load(a), load(b)
        if ra is None or rb is None:
            continue
        pairs.append((a, b))
        comps.append(compare(ra, rb))
    apply_holm(comps)
    return {pair: c.verdict.startswith("distinguable") for pair, c in zip(pairs, comps)}


def per_subject(run: dict, metric: str = "dice_mean") -> tuple[list[str], np.ndarray]:
    sids = sorted(run["per_subject"], key=int)
    return sids, np.array([run["per_subject"][s][metric] for s in sids])


def mean_ci(values: np.ndarray) -> tuple[float, float]:
    """(moyenne, demi-largeur de l'IC à 95 %) par la loi de Student : n = 10, pas la normale."""
    n = values.size
    if n < 2:
        return float(values.mean()), 0.0
    half = sps.t.ppf(0.5 + CONF / 2, n - 1) * values.std(ddof=1) / np.sqrt(n)
    return float(values.mean()), float(half)


def paired_ci(run_a: dict, run_b: dict) -> tuple[float, float, int]:
    """Delta apparié b - a sur les sujets communs, sa demi-largeur d'IC, et n."""
    sa, va = per_subject(run_a)
    sb, vb = per_subject(run_b)
    common = [s for s in sa if s in set(sb)]
    d = np.array([run_b["per_subject"][s]["dice_mean"] - run_a["per_subject"][s]["dice_mean"] for s in common])
    m, h = mean_ci(d)
    return m, h, d.size


def main() -> None:
    use()
    runs = {k: r for k, _, _ in STEPS if (r := load(k)) is not None}
    steps = [(k, lab, ref) for k, lab, ref in STEPS if k in runs]
    if not steps:
        raise SystemExit("aucun résultat dans results/")

    fig, (ax_abs, ax_del) = plt.subplots(1, 2, figsize=(6.6, 3.3), gridspec_kw={"width_ratios": [1.0, 1.0]})
    y = np.arange(len(steps))[::-1]
    labels = [lab for _, lab, _ in steps]

    # --- (a) Dice absolu -------------------------------------------------------------------
    means, halves = [], []
    for key, _, _ in steps:
        m, h = mean_ci(per_subject(runs[key])[1])
        means.append(m)
        halves.append(h)
    # Panneau (a) : on met en accent le MEILLEUR Dice, pas une configuration nommée en dur.
    # La significativité n'a pas de sens sur des valeurs absolues — c'est le panneau (b) qui
    # la porte.
    best = int(np.argmax(means))
    colors = [ACCENT if i == best else NEUTRAL_FILL for i in range(len(steps))]
    ax_abs.barh(y, means, height=0.62, color=colors, edgecolor=NEUTRAL_EDGE, lw=0.7, zorder=2)
    ax_abs.errorbar(means, y, xerr=halves, fmt="none", ecolor=NEUTRAL_TEXT, elinewidth=0.8, capsize=2.5, zorder=3)
    for yi, m, h, key in zip(y, means, halves, [k for k, _, _ in steps]):
        ax_abs.text(m + h + 0.0011, yi, f"{m:.4f}  ({runs[key]['n_params']} p.)", va="center",
                    fontsize=6.4, color=NEUTRAL_TEXT)
    lo = min(np.array(means) - np.array(halves))
    ax_abs.set_xlim(lo - 0.003, max(means) + max(halves) + 0.0115)
    ax_abs.set_yticks(y, labels, fontsize=6.6)
    ax_abs.set_xlabel("Dice moyen, IC 95 % (axe tronqué)")
    ax_abs.set_title("(a) valeurs absolues : tout se chevauche", fontsize=7.4, pad=5)

    # --- (b) delta apparié -----------------------------------------------------------------
    dmeans, dhalves, dlabels = [], [], []
    for key, lab, ref in steps:
        if ref is None or ref not in runs:
            dmeans.append(np.nan)
            dhalves.append(0.0)
            dlabels.append("référence")
            continue
        m, h, _ = paired_ci(runs[ref], runs[key])
        dmeans.append(m)
        dhalves.append(h)
        dlabels.append("")
    finite = ~np.isnan(dmeans)
    verdicts = declared_verdicts()
    signif = [bool(f and verdicts.get((ref, key), False)) for f, (key, _, ref) in zip(finite, steps)]
    dcolors = [ACCENT if s else NEUTRAL_FILL for s in signif]
    ax_del.axvline(0.0, color=NEUTRAL_EDGE, lw=0.7, zorder=1)
    ax_del.barh(y[finite], np.array(dmeans)[finite], height=0.62,
                color=[c for c, f in zip(dcolors, finite) if f],
                edgecolor=NEUTRAL_EDGE, lw=0.7, zorder=2)
    ax_del.errorbar(np.array(dmeans)[finite], y[finite], xerr=np.array(dhalves)[finite], fmt="none",
                    ecolor=NEUTRAL_TEXT, elinewidth=0.8, capsize=2.5, zorder=3)
    for yi, m, h, f in zip(y, dmeans, dhalves, finite):
        if not f:
            ax_del.text(0.0, yi - 0.08, "  point de départ de l'ablation", va="center",
                        fontsize=6.4, color=NEUTRAL_TEXT)
            continue
        side = 1 if m >= 0 else -1
        ax_del.text(m + side * (h + 0.0016), yi, f"{m:+.4f}", va="center",
                    ha="left" if side > 0 else "right", fontsize=6.4, color=NEUTRAL_TEXT)
    span = max(abs(np.array(dmeans)[finite]) + np.array(dhalves)[finite]) if finite.any() else 0.01
    ax_del.set_xlim(-span * 1.9, span * 1.9)
    ax_del.set_yticks(y, [""] * len(y))
    ax_del.set_xlabel("Δ Dice apparié contre l'étape précédente, IC 95 %")
    ax_del.set_title("(b) comparaisons appariées : le bruit s'annule", fontsize=7.4, pad=5)

    for ax in (ax_abs, ax_del):
        ax.grid(True, axis="x", lw=0.3, color="0.88", zorder=0)
        ax.set_axisbelow(True)
        ax.tick_params(length=2.5)
        for side in ("top", "right"):
            ax.spines[side].set_visible(False)

    fig.text(0.5, -0.035,
             "En accent, les étapes déclarées distinguables du bruit (§ 4). L'axe de (a) est "
             "tronqué : les écarts valent quelques millièmes de Dice.\n"
             "Les intervalles sont ceux de la moyenne sur n = 10, loi de Student ; en cas de "
             "divergence avec le test déclaré, c'est le test qui tranche.",
             ha="center", va="top", fontsize=7.0, color=NEUTRAL_TEXT, linespacing=1.5)
    fig.tight_layout()
    fig.savefig(OUT, format="pdf", bbox_inches="tight")
    print(f"{OUT}")
    for (key, _, ref), m, h in zip(steps, dmeans, dhalves):
        if not np.isnan(m):
            print(f"  {key:22s} Δ={m:+.4f} ± {h:.4f} contre {ref}")


if __name__ == "__main__":
    main()
