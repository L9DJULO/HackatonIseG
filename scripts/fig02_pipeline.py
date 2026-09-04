"""Figure 2 — le pipeline, avec le coût en paramètres appris rendu visible.

Le schéma sert un seul argument : une seule étape mémorise quelque chose du jeu
d'entraînement. Toutes les autres se recalculent sur le sujet qu'on est en train de
segmenter et ne transportent rien. L'étape qui coûte est la seule en accent et en trait
épais ; les nombres de colonnes par bloc et le nombre de paramètres sont lus dans le JSON
de la configuration finale, ils ne sont pas écrits à la main.

Usage : python scripts/fig02_pipeline.py -> report/assets/fig02_pipeline.pdf
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use("pdf")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.figstyle import ACCENT, ACCENT_LIGHT, NEUTRAL_EDGE, NEUTRAL_FILL, NEUTRAL_TEXT, use  # noqa: E402

BLOCKS = [
    ("A", "intensités", "intensity"),
    ("B", "gaussiennes", "gaussian"),
    ("C", "spatial", "spatial"),
    ("D", "morphologie", "morpho"),
    ("E", "symétrie", "symmetry"),
    ("F", "contexte", "context"),
]


def counts_from_results() -> tuple[dict[str, int], int, int]:
    r = json.loads((ROOT / "results" / "logreg_final.json").read_text())
    per_block: dict[str, int] = {}
    for name in r["feature_names"]:
        per_block[name.split("/", 1)[0]] = per_block.get(name.split("/", 1)[0], 0) + 1
    return per_block, int(r["n_features"]), int(r["n_params"])


def box(ax, x, y, w, h, text, *, accent=False, dashed=False, fs=8.0):
    ax.add_patch(FancyBboxPatch(
        (x, y), w, h, boxstyle="round,pad=0.006,rounding_size=0.012",
        linewidth=1.8 if accent else 0.8,
        linestyle="--" if dashed else "-",
        facecolor=ACCENT_LIGHT if accent else NEUTRAL_FILL,
        edgecolor=ACCENT if accent else NEUTRAL_EDGE, zorder=2))
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=fs,
            color=ACCENT if accent else NEUTRAL_TEXT, zorder=3, linespacing=1.35)


def arrow(ax, x0, y0, x1, y1, rad=0.0):
    ax.add_patch(FancyArrowPatch(
        (x0, y0), (x1, y1), arrowstyle="-|>", mutation_scale=8, linewidth=0.9,
        color=NEUTRAL_EDGE, connectionstyle=f"arc3,rad={rad}",
        shrinkA=0, shrinkB=0, zorder=1))


def main() -> None:
    use()
    per_block, n_features, n_params = counts_from_results()

    fig, ax = plt.subplots(figsize=(6.4, 3.35))
    ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.axis("off")

    # ---- rangée 1 : entrée, les six blocs, la matrice ----------------------------
    box(ax, 0.005, 0.615, 0.104, 0.20, "T1, T2\ndu sujet", fs=7.8)

    gx, gy, gw, gh = 0.150, 0.545, 0.500, 0.345
    ax.add_patch(FancyBboxPatch(
        (gx, gy), gw, gh, boxstyle="round,pad=0.008,rounding_size=0.012",
        linewidth=0.8, linestyle=(0, (4, 2)), facecolor="none", edgecolor=NEUTRAL_EDGE, zorder=1))
    ax.text(gx + gw / 2, gy + gh + 0.045, "six blocs de descripteurs — 0 paramètre appris",
            ha="center", va="center", fontsize=8.0, color=NEUTRAL_TEXT)
    bw, bh = 0.152, 0.125
    for i, (letter, label, key) in enumerate(BLOCKS):
        cx = gx + 0.015 + (i % 3) * (bw + 0.008)
        cy = gy + gh - 0.045 - (i // 3) * (bh + 0.045)
        box(ax, cx, cy - bh, bw, bh, f"{letter}  {label}\n{per_block[key]} colonnes", fs=6.9)

    box(ax, 0.700, 0.615, 0.150, 0.20,
        f"une ligne\npar voxel\n{n_features} colonnes", fs=7.4)

    arrow(ax, 0.109, 0.715, 0.148, 0.715)
    arrow(ax, 0.652, 0.715, 0.698, 0.715)
    # renvoi de la rangée 1 vers la rangée 2
    arrow(ax, 0.850, 0.715, 0.910, 0.715)
    ax.plot([0.910, 0.968, 0.968, 0.092, 0.092], [0.715, 0.715, 0.430, 0.430, 0.350],
            color=NEUTRAL_EDGE, linewidth=0.9, zorder=1, solid_joinstyle="round")
    arrow(ax, 0.092, 0.355, 0.092, 0.325)

    # ---- rangée 2 : standardisation, classifieur, priors, sortie ------------------
    y, h = 0.105, 0.215
    widths = [0.180, 0.250, 0.140, 0.160, 0.115]
    texts = [("standardisation\nintra-sujet", False, False, 7.2),
             (f"régression logistique\nmultinomiale\n{n_params} paramètres appris", True, False, 7.4),
             ("correction des\npriors, argmax", False, False, 7.0),
             ("post-traitement\n(§ 3.4)", False, True, 6.8),
             ("3 tissus\nsegmentés", False, False, 7.2)]
    xs, cur = [], 0.002
    for w in widths:
        xs.append(cur)
        cur += w + 0.036
    for x, w, (t, acc, dsh, fs) in zip(xs, widths, texts):
        box(ax, x, y, w, h, t, accent=acc, dashed=dsh, fs=fs)
    for x, w in zip(xs[:-1], widths[:-1]):
        arrow(ax, x + w + 0.003, y + h / 2, x + w + 0.033, y + h / 2)

    ax.text(0.001, 0.030,
            "En accent et en trait épais : la seule étape qui mémorise le jeu d'entraînement. "
            "Tout le reste se recalcule sur le sujet segmenté.",
            ha="left", va="center", fontsize=7.2, color=NEUTRAL_TEXT)

    out = ROOT / "report" / "assets" / "fig02_pipeline.pdf"
    fig.savefig(out, format="pdf", bbox_inches="tight", pad_inches=0.02)
    print(f"{out}  {n_features} colonnes, {n_params} paramètres")


if __name__ == "__main__":
    main()
