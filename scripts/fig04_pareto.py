"""Figure 4 : front de Pareto (paramètres, Dice), abscisse logarithmique.

C'est la figure qui porte l'argument central du rapport, et la seule qui met nos chiffres à
côté de ceux du challenge. Elle doit donc être irréprochable sur deux points.

1. TOUT CHIFFRE PUBLIÉ EST SOURCÉ, ET AUCUN N'EST ESTIMÉ. Les deux points de référence sont
   les seules méthodes pour lesquelles on dispose À LA FOIS d'un Dice officiel et d'un compte
   de paramètres publié. On ne place sur la figure aucune méthode dont il faudrait deviner le
   nombre de paramètres : une estimation d'ordre de grandeur a sa place dans le texte, pas
   dans un nuage de points où elle se lirait comme une mesure.

2. DEUX RÉGIMES D'ÉVALUATION, DISTINGUÉS PAR LE SYMBOLE. Le front en trait plein est un
   leave-one-out sur les 10 sujets annotés : il sert à comparer nos configurations ENTRE ELLES,
   pas au challenge. Le point plein isolé est le score OFFICIEL que le serveur du challenge a
   rendu pour notre soumission, sur les mêmes 13 sujets de test que les références publiées :
   celui-là, et lui seul, se compare directement à elles.

Usage : python scripts/fig04_pareto.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.figstyle import ACCENT, NEUTRAL_EDGE, NEUTRAL_FILL, NEUTRAL_TEXT, use  # noqa: E402

RESULTS = ROOT / "results"
OUT = ROOT / "report" / "assets" / "fig04_pareto.pdf"

# Nos configurations, dans l'ordre de lecture du rapport.
OURS = [
    ("logreg_ABC", "A+B+C"),
    ("logreg_ABCD_p0", "palier 0"),
    ("logreg_ABCD_p1", "palier 1"),
    ("logreg_ABCD_p2", "palier 2"),
    ("logreg_ABCD_p3", "palier 3"),
    ("logreg_final", "finale"),
    ("select_k40", "sélection K=40"),
    ("autocontext_final", "auto-contexte"),
]

# --- Points de référence publiés ----------------------------------------------------------
# Dice : tableau officiel du challenge, https://iseg2017.web.unc.edu/evaluation/ (13 sujets de
#        test, évaluation par le serveur des organisateurs).
# Paramètres : comptes PUBLIÉS, pas des estimations.
#   MSL_SKKU      1 550 000  « 1.55 million learnable parameters », Wang et al., IEEE TMI 2019.
#   HyperDenseNet 10 349 450  Dolz et al., table 4 (9 518 850 conv + 830 600 fully-connected).
PUBLISHED = [
    ("MSL_SKKU", 1_550_000, (0.958, 0.923, 0.904)),
    ("HyperDenseNet", 10_349_450, (0.956, 0.920, 0.901)),
]

OFFICIEL = ROOT / "results" / "official_test.json"
"""Notre score officiel, rendu par le serveur du challenge sur les 13 sujets de test. Produit
par la même configuration que le point « auto-contexte » du front, mais entraînée sur les dix
sujets annotés au lieu de neuf : c'est pourquoi les deux points ne se superposent pas."""


def load(name: str) -> dict | None:
    p = RESULTS / f"{name}.json"
    return json.loads(p.read_text()) if p.exists() else None


def pareto_front(points: list[tuple[float, float]]) -> list[tuple[float, float]]:
    """Points non dominés : aucun autre n'a à la fois moins de paramètres et un meilleur Dice."""
    front = [p for p in points if not any(q[0] <= p[0] and q[1] > p[1] for q in points)]
    return sorted(front)


def main() -> None:
    use()
    ours = [(r["n_params"], r["mean"]["dice_mean"], lab) for key, lab in OURS if (r := load(key))]
    if not ours:
        raise SystemExit("aucun résultat dans results/ : lancer la grille d'abord")
    deg = load("degenerate_baseline")

    fig, ax = plt.subplots(figsize=(5.4, 3.5))
    ax.set_xscale("log")

    front = pareto_front([(x, y) for x, y, _ in ours])
    ax.plot([p[0] for p in front], [p[1] for p in front], "-", color=ACCENT, lw=1.0, zorder=2,
            label="front de Pareto de nos configurations")

    xs, ys = [p[0] for p in ours], [p[1] for p in ours]
    ax.scatter(xs, ys, s=34, facecolor=NEUTRAL_FILL, edgecolor=NEUTRAL_EDGE, lw=0.8, zorder=3)
    fin = next((p for p in ours if p[2] == "auto-contexte"), None) or next((p for p in ours if p[2] == "finale"), None)
    if fin:
        ax.scatter([fin[0]], [fin[1]], s=52, facecolor=ACCENT, edgecolor="none", zorder=4)
    ax.annotate("nos configurations", (min(xs), float(np.max(ys))),
                textcoords="offset points", xytext=(-10, 12), ha="right", fontsize=6.8,
                color=NEUTRAL_TEXT,
                arrowprops=dict(arrowstyle="-", lw=0.5, color=NEUTRAL_EDGE, shrinkA=2, shrinkB=4))

    if deg:
        ax.scatter([deg["n_params"]], [deg["dice_mean"]], s=34, marker="x", color=NEUTRAL_EDGE, lw=1.0, zorder=3)
        ax.annotate("classifieur dégénéré\n(1 paramètre)", (deg["n_params"], deg["dice_mean"]),
                    textcoords="offset points", xytext=(6, 4), fontsize=6.8, color=NEUTRAL_TEXT)

    # notre point OFFICIEL : même évaluation que les références publiées
    officiel = json.loads(OFFICIEL.read_text()) if OFFICIEL.exists() else None
    if officiel:
        ox, oy = officiel["n_params"], officiel["mean"]["dice_mean"]
        ax.scatter([ox], [oy], s=64, marker="D", facecolor=ACCENT, edgecolor="white", lw=0.8, zorder=6,
                   label="nous, score officiel du serveur (13 sujets de test)")
        ax.annotate(f"notre soumission\n{oy:.4f}", (ox, oy), textcoords="offset points",
                    xytext=(14, -20), ha="left", fontsize=6.8, color=ACCENT, fontweight="bold")

    px = [p[1] for p in PUBLISHED]
    py = [float(np.mean(p[2])) for p in PUBLISHED]
    ax.scatter(px, py, s=42, marker="s", facecolor="none", edgecolor=NEUTRAL_EDGE, lw=1.0, zorder=3,
               label="challenge iSeg-2017, méthodes publiées (mêmes 13 sujets)")
    # décalages alternés : les deux points sont proches en ordonnée, leurs étiquettes se
    # chevaucheraient si elles étaient placées du même côté.
    for (name, x, _), y, dy in zip(PUBLISHED, py, (13, -15)):
        ax.annotate(name, (x, y), textcoords="offset points", xytext=(0, dy), ha="center",
                    fontsize=6.8, color=NEUTRAL_TEXT)

    ancre = (officiel["n_params"], officiel["mean"]["dice_mean"]) if officiel else (fin[0], fin[1]) if fin else None
    if ancre:
        ax.annotate(
            "", xy=(PUBLISHED[0][1], py[0]), xytext=ancre,
            arrowprops=dict(arrowstyle="-", ls=":", lw=0.7, color=NEUTRAL_EDGE, shrinkA=6, shrinkB=8),
        )
        ratio = PUBLISHED[0][1] / ancre[0]
        ax.text(np.sqrt(ancre[0] * PUBLISHED[0][1]) * 0.62, (ancre[1] + py[0]) / 2 + 0.055,
                f"$10^2$ contre $10^6$ paramètres\npour {ancre[1] / py[0]:.0%} de son Dice",
                fontsize=6.8, ha="center", color=NEUTRAL_TEXT)

    # --- encart : nos configurations sont toutes entre 250 et 570 paramètres, donc
    #     indiscernables sur trois décades. Le zoom rend l'ablation lisible sans quitter
    #     la figure qui porte l'argument.
    inset = ax.inset_axes([0.44, 0.10, 0.45, 0.44])
    inset.plot([p[0] for p in front], [p[1] for p in front], "-", color=ACCENT, lw=1.0, zorder=2)
    inset.scatter(xs, ys, s=26, facecolor=NEUTRAL_FILL, edgecolor=NEUTRAL_EDGE, lw=0.8, zorder=3)
    if fin:
        inset.scatter([fin[0]], [fin[1]], s=40, facecolor=ACCENT, edgecolor="none", zorder=4)
    # les paliers 2 et 3 sont à 408 et 426 paramètres pour le même Dice : sans décalages
    # explicites, leurs étiquettes se superposent.
    # L'encart porte la FORME du front, pas le détail de l'ablation : celui-ci est la figure 5.
    # On n'étiquette donc que les points qui font l'argument — les deux extrémités du front et
    # la configuration de référence. Étiqueter les quatre paliers intermédiaires, tous groupés
    # entre 324 et 564 paramètres, rendrait l'encart illisible sans rien ajouter.
    placements = {"sélection K=40": (30, 9), "A+B+C": (24, -12),
                  "finale": (-4, 10), "auto-contexte": (-32, -11)}
    for x, y, lab in ours:
        if lab not in placements:
            continue
        style = dict(color=ACCENT, fontweight="bold") if fin and lab == fin[2] else dict(color=NEUTRAL_TEXT)
        inset.annotate(lab, (x, y), textcoords="offset points", xytext=placements[lab],
                       ha="center", fontsize=6.0, **style)
    inset.set_xlim(min(xs) * 0.80, max(xs) * 1.14)
    inset.set_ylim(min(ys) - 0.0042, max(ys) + 0.0030)
    inset.tick_params(labelsize=5.8, length=2, pad=1.5)
    inset.set_xlabel("paramètres", fontsize=6.0, labelpad=1.0)
    inset.set_ylabel("Dice moyen", fontsize=6.0, labelpad=1.0)
    inset.set_title("détail : le front, des 163 paramètres aux 939", fontsize=6.2, pad=3.0, color=NEUTRAL_TEXT)
    for spine in inset.spines.values():
        spine.set_linewidth(0.5)
        spine.set_color(NEUTRAL_EDGE)
    inset.set_facecolor("white")
    inset.grid(True, lw=0.25, color="0.9")
    inset.set_axisbelow(True)

    ax.set_xlabel("paramètres appris (échelle logarithmique)")
    ax.set_ylabel("Dice moyen sur les trois tissus")
    ax.set_ylim(0.15, 1.06)
    ax.set_xlim(0.5, 3e7)
    ax.grid(True, which="major", axis="both", lw=0.3, color="0.85", zorder=0)
    ax.set_axisbelow(True)
    ax.legend(loc="upper center", frameon=False, fontsize=6.8, ncol=2,
              bbox_to_anchor=(0.5, -0.16), columnspacing=1.6)
    fig.text(0.5, -0.13,
             "Le losange et les carrés sont évalués sur les MÊMES 13 sujets de test par le serveur "
             "des organisateurs : ils se comparent directement.\nLe front en trait plein est un "
             "leave-one-out sur les 10 sujets annotés — il sert à comparer nos configurations "
             "entre elles, pas au challenge.",
             ha="center", va="top", fontsize=6.2, color=NEUTRAL_TEXT)
    fig.savefig(OUT, format="pdf", bbox_inches="tight")
    print(f"{OUT}")
    if officiel:
        print(f"  soumission officielle : {ox} paramètres, Dice {oy:.4f} sur 13 sujets de test")
        print(f"  MSL_SKKU : {PUBLISHED[0][1]} paramètres, Dice {py[0]:.4f} "
              f"-> ×{PUBLISHED[0][1] / ox:.0f} de paramètres, {oy / py[0]:.1%} de son Dice")


if __name__ == "__main__":
    main()
