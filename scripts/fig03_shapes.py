"""Figure 3 — arbre des formes : emboîtement, arbre d'inclusion, remontée de branche.

L'arbre n'est pas dessiné à la main. Il est calculé par higra sur une image synthétique à
cinq niveaux, avec exactement la même fonction que le bloc D en 3D, et la figure affiche
ses vrais nœuds, leurs vraies aires et leurs vrais liens de parenté.

L'image est construite pour montrer l'auto-dualité : une forme SOMBRE (niveau 1) est
emboîtée dans une forme CLAIRE (niveau 4), et l'arbre les traite de la même façon. Ni un
max-tree ni un min-tree ne les mettrait sur la même branche.

Le panneau de droite porte l'ordonnée en aire, en échelle logarithmique. La remontée de
branche devient alors lisible directement : le premier ancêtre d'aire supérieure à un
seuil est le premier nœud de la branche situé au-dessus de la ligne du seuil.

Usage : python scripts/fig03_shapes.py -> report/assets/fig03_shapes.pdf
"""
from __future__ import annotations

import sys
from pathlib import Path

import matplotlib

matplotlib.use("pdf")
import matplotlib.pyplot as plt  # noqa: E402
import matplotlib.patheffects as pe  # noqa: E402
import numpy as np  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.figstyle import ACCENT, NEUTRAL_EDGE, NEUTRAL_TEXT, use  # noqa: E402

SIZE = 96
THRESHOLDS = (200, 1000, 5000)   # analogues 2D des seuils 3D (100, 1000, 10^4, 10^5) voxels
P = (35, 31)                     # le voxel dont on suit la branche


def toy_image() -> np.ndarray:
    yy, xx = np.mgrid[0:SIZE, 0:SIZE]
    def disc(cy, cx, r):
        return (yy - cy) ** 2 + (xx - cx) ** 2 <= r * r
    img = np.full((SIZE, SIZE), 2, dtype=np.uint8)
    img[disc(42, 40, 32)] = 4     # forme claire
    img[disc(38, 34, 16)] = 1     # forme SOMBRE emboîtée dans la claire : auto-dualité
    img[disc(35, 31, 6)] = 5      # forme claire au cœur de la sombre, contient P
    img[disc(43, 40, 4)] = 5      # sa sœur
    img[disc(80, 80, 10)] = 3     # forme disjointe
    return img


def build():
    import higra as hg
    img = toy_image()
    tree, alt = hg.component_tree_tree_of_shapes_image2d(
        img, padding="none", original_size=True, immersion=True)
    nl, nn = tree.num_leaves(), tree.num_vertices()
    par = np.asarray(tree.parents())
    area = np.asarray(hg.attribute_area(tree))

    nodes = list(range(nl, nn))
    support = {n: np.zeros(nl, dtype=bool) for n in nodes}
    cur = par[:nl].copy()
    while True:
        for n in nodes:
            support[n] |= cur == n
        nxt = par[cur]
        if np.array_equal(nxt, cur):
            break
        cur = nxt

    chain, n = [], par[P[0] * SIZE + P[1]]
    while True:
        chain.append(int(n))
        if par[n] == n:
            break
        n = int(par[n])
    return img, par, area, np.asarray(alt), nodes, support, chain, nl


def layout(nodes, par) -> dict[int, float]:
    """x de chaque nœud : les nœuds sans enfant interne à la suite, les autres au barycentre."""
    children = {n: [] for n in nodes}
    for n in nodes:
        if par[n] != n:
            children[int(par[n])].append(n)
    root = next(n for n in nodes if par[n] == n)
    x, counter = {}, [0.0]

    def visit(n):
        if not children[n]:
            x[n] = counter[0]
            counter[0] += 1.0
            return x[n]
        xs = [visit(c) for c in sorted(children[n])]
        x[n] = float(np.mean(xs))
        return x[n]

    visit(root)
    return x


def main() -> None:
    use()
    img, par, area, alt, nodes, support, chain, nl = build()
    x = layout(nodes, par)
    chain_set = set(chain)

    fig = plt.figure(figsize=(6.4, 2.95))
    gs = fig.add_gridspec(1, 2, width_ratios=[1.0, 1.32], wspace=0.24,
                          left=0.015, right=0.965, top=0.90, bottom=0.13)

    # ---- (a) emboîtement des formes ------------------------------------------------
    ax = fig.add_subplot(gs[0, 0])
    ax.imshow(img, cmap="gray", vmin=0, vmax=6, interpolation="nearest")
    for n in nodes:
        if par[n] == n:
            continue
        m = support[n].reshape(SIZE, SIZE).astype(float)
        inchain = n in chain_set
        ax.contour(m, levels=[0.5], colors=[ACCENT if inchain else "#FFFFFF"],
                   linewidths=1.7 if inchain else 0.8,
                   linestyles=["solid" if inchain else "dashed"])
    ax.plot([P[1]], [P[0]], marker="o", markersize=3.6, color=ACCENT,
            markeredgecolor="white", markeredgewidth=0.6, zorder=5)
    ax.annotate("p", (P[1], P[0]), textcoords="offset points", xytext=(6, 5),
                fontsize=9.5, color=ACCENT, fontweight="bold",
                path_effects=[pe.withStroke(linewidth=2.2, foreground="white")])
    ax.set_xticks([]); ax.set_yticks([])
    for sp in ax.spines.values():
        sp.set_edgecolor(NEUTRAL_EDGE)
        sp.set_linewidth(0.6)
    ax.set_title("(a) formes emboîtées", fontsize=8.5, pad=4)

    # ---- (b) arbre d'inclusion, ordonnée en aire ------------------------------------
    ax = fig.add_subplot(gs[0, 1])
    for n in nodes:
        if par[n] == n:
            continue
        p = int(par[n])
        inchain = n in chain_set and p in chain_set
        ax.plot([x[n], x[p]], [area[n], area[p]],
                color=ACCENT if inchain else NEUTRAL_EDGE,
                linewidth=2.0 if inchain else 0.8, zorder=2 if inchain else 1,
                solid_capstyle="round")
    for n in nodes:
        grey = 0.10 + 0.80 * (float(alt[n]) - 1.0) / 4.0
        ax.plot([x[n]], [area[n]], marker="o", markersize=9.5 if n in chain_set else 7.0,
                markerfacecolor=str(grey),
                markeredgecolor=ACCENT if n in chain_set else NEUTRAL_EDGE,
                markeredgewidth=1.6 if n in chain_set else 0.8, zorder=3)

    for i, t in enumerate(THRESHOLDS, 1):
        ax.axhline(t, color=NEUTRAL_EDGE, linewidth=0.6, linestyle=(0, (4, 3)), zorder=0)
        ax.text(0.998, t, f"$T_{i}$ ", fontsize=7.5, va="bottom", ha="right",
                color=NEUTRAL_TEXT, transform=ax.get_yaxis_transform())
        anc = next(c for c in chain if area[c] >= t)
        ax.annotate(f"$a(T_{i})$", (x[anc], area[anc]), textcoords="offset points",
                    xytext=(10, -1), fontsize=7.8, color=ACCENT, va="center")

    ax.annotate("p", (x[chain[0]], area[chain[0]]), textcoords="offset points",
                xytext=(-14, -1), fontsize=9, color=ACCENT, va="center", fontweight="bold")
    ax.set_yscale("log")
    ax.set_ylabel("aire du nœud (pixels)")
    ax.set_xticks([])
    ax.set_xlim(-0.85, max(x.values()) + 1.35)
    ax.set_ylim(32, 3.4e4)
    for sp in ("top", "right", "bottom"):
        ax.spines[sp].set_visible(False)
    ax.set_title("(b) arbre d'inclusion et remontée de branche", fontsize=8.5, pad=4)

    out = ROOT / "report" / "assets" / "fig03_shapes.pdf"
    fig.savefig(out, format="pdf")
    print(f"{out}  {len(nodes)} nœuds, branche de p : "
          + " -> ".join(f"aire {int(area[c])}" for c in chain))


if __name__ == "__main__":
    main()
