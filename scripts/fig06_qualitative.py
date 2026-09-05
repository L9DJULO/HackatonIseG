"""Figure 6 : le meilleur et le pire sujet, avec leur carte d'erreur.

Une figure qualitative n'a d'intérêt que si elle montre aussi le mauvais cas. Celle-ci met en
regard le sujet le mieux segmenté et le moins bien segmenté du leave-one-out, avec la même
échelle, la même coupe choisie par la même règle, et la carte des erreurs. Le pire cas est
commenté dans le texte plutôt que caché.

RÈGLE DE CHOIX DE LA COUPE, identique pour les deux sujets : la coupe axiale contenant le plus
de voxels du masque cérébral. Choisir la coupe la plus flatteuse pour l'un et la plus parlante
pour l'autre rendrait la comparaison malhonnête, et choisir la coupe la plus fautive
donnerait une image plus sombre que la réalité.

Les prédictions sont relues depuis results/proba/<run>/subject-*.npz, écrites par la boucle
leave-one-out : ce sont donc bien des prédictions faites sur un sujet que le modèle n'avait
jamais vu.

Usage : python scripts/fig06_qualitative.py [--run autocontext_final]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import ListedColormap
from matplotlib.patches import Patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.figstyle import ACCENT, COL_CSF, COL_GM, COL_WM, NEUTRAL_TEXT, use  # noqa: E402
from src.io import load_subject  # noqa: E402

LABELS = {1: "LCR", 2: "substance grise", 3: "substance blanche"}
TISSUE_CMAP = ListedColormap(["#0B0B0B", COL_CSF, COL_GM, COL_WM])


def best_and_worst(run: dict) -> tuple[int, int]:
    per = {int(k): v["dice_mean"] for k, v in run["per_subject"].items()}
    return max(per, key=per.get), min(per, key=per.get)


def widest_axial_slice(mask: np.ndarray) -> int:
    """Coupe axiale contenant le plus de voxels du masque. Même règle pour les deux sujets."""
    return int(np.argmax(mask.reshape(-1, mask.shape[2]).sum(axis=0)))


def panel(ax, image, title, cmap, **kw):
    ax.imshow(image.T, origin="lower", cmap=cmap, interpolation="nearest", **kw)
    ax.set_title(title, fontsize=7.2, pad=3, color=NEUTRAL_TEXT)
    ax.axis("off")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", default="autocontext_final")
    args = ap.parse_args()
    use()

    run = json.loads((ROOT / "results" / f"{args.run}.json").read_text())
    best, worst = best_and_worst(run)
    proba_dir = ROOT / "results" / "proba" / args.run

    fig, axes = plt.subplots(2, 4, figsize=(7.2, 4.3))
    infos = []
    for row, (sid, tag) in enumerate(((best, "meilleur"), (worst, "pire"))):
        s = load_subject(sid, ROOT / "data")
        d = np.load(proba_dir / f"subject-{sid}.npz")
        pred = np.zeros(s.mask.shape, np.uint8)
        pred[d["mask"]] = np.argmax(d["proba"].astype(np.float32), axis=1) + 1
        gt = s.label
        k = widest_axial_slice(s.mask)

        t1, g, p, m = s.t1[:, :, k], gt[:, :, k], pred[:, :, k], s.mask[:, :, k]
        err = np.zeros_like(g)
        err[m & (g != p)] = g[m & (g != p)]  # colorée par le tissu QU'ON A MANQUÉ

        dice = run["per_subject"][str(sid)]["dice_mean"]
        rate = float((m & (g != p)).sum() / max(m.sum(), 1))
        infos.append((sid, tag, dice, rate, k))

        panel(axes[row, 0], t1, f"sujet {sid} ({tag}) — T1", "gray")
        panel(axes[row, 1], g, "vérité terrain", TISSUE_CMAP, vmin=0, vmax=3)
        panel(axes[row, 2], p, f"notre prédiction — Dice {dice:.3f}", TISSUE_CMAP, vmin=0, vmax=3)
        panel(axes[row, 3], err, f"erreurs — {rate:.1%} de la coupe", TISSUE_CMAP, vmin=0, vmax=3)
        axes[row, 3].imshow(np.where(m.T, 0.12, 0.0), origin="lower", cmap="gray_r",
                            alpha=0.25, vmin=0, vmax=1, interpolation="nearest", zorder=0)

    handles = [Patch(facecolor=c, edgecolor="0.4", lw=0.5, label=LABELS[i])
               for i, c in ((1, COL_CSF), (2, COL_GM), (3, COL_WM))]
    fig.legend(handles=handles, loc="lower center", ncol=3, frameon=False, fontsize=7,
               bbox_to_anchor=(0.5, 0.0))
    # Pas de légende interne : la règle de choix de la coupe et le codage de la carte d'erreur
    # sont dans la légende LaTeX de la figure, les répéter ici ferait doublon dans le rapport.
    fig.tight_layout(rect=(0, 0.045, 1, 1))
    out = ROOT / "report" / "assets" / "fig06_qualitative.pdf"
    fig.savefig(out, format="pdf", bbox_inches="tight")
    print(out)
    for sid, tag, dice, rate, k in infos:
        print(f"  sujet {sid} ({tag}) : Dice {dice:.4f}, coupe {k}, {rate:.2%} de voxels erronés sur la coupe")


if __name__ == "__main__":
    main()
