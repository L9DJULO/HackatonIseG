"""Figure 1 — la phase isointense, montrée puis chiffrée.

Quatre panneaux sur le même sujet et la même coupe axiale : T1, T2, segmentation manuelle
de référence, et les histogrammes d'intensité de la substance grise et de la substance
blanche superposés pour les deux modalités. Le dernier panneau est le cœur de la figure :
l'aire grisée est exactement le coefficient de recouvrement OVL défini dans
scripts/isointensity.py, et c'est lui qui interdit toute décision fondée sur la seule
valeur d'un voxel.

Le sujet est choisi pour sa TYPICITÉ, mesurée sur les quatre recouvrements de
results/isointensity.json : c'est celui dont l'écart réduit maximal aux dix sujets est le
plus petit. La coupe est choisie pour sa LISIBILITÉ : celle qui maximise min(n_SG, n_SB),
donc celle où l'interface entre les deux tissus est la plus étendue.

Usage : python scripts/fig01_isointense.py  ->  report/assets/fig01_isointense.pdf
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use("pdf")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from matplotlib.colors import ListedColormap  # noqa: E402
from matplotlib.patches import Patch  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.io import load_subject  # noqa: E402
from scripts.isointensity import N_BINS, SIGNALS, SUBJECTS  # noqa: E402

from scripts.figstyle import COL_CSF, COL_GM, COL_WM, EDGE_GM, EDGE_WM  # noqa: E402
import scripts.figstyle as figstyle  # noqa: E402

LABELS = {1: "LCR", 2: "substance grise", 3: "substance blanche"}

figstyle.use()


def pick_subject() -> tuple[int, dict]:
    """Le sujet le moins atypique : plus petit écart réduit maximal sur les quatre mesures."""
    d = json.loads((ROOT / "results" / "isointensity.json").read_text())
    ps, sm = d["per_subject"], d["summary"]
    scores = {
        sid: max(abs((ps[str(sid)][s] - sm[s]["mean"]) / sm[s]["std"]) for s in SIGNALS)
        for sid in SUBJECTS
    }
    best = min(scores, key=scores.get)
    return best, {"atypicality": scores, "facts": d}


def pick_slice(label: np.ndarray) -> int:
    """La coupe axiale de plus grande interface : celle qui maximise min(n_SG, n_SB)."""
    return int(np.argmax(np.minimum((label == 2).sum(axis=(0, 1)), (label == 3).sum(axis=(0, 1)))))


def crop(mask2d: np.ndarray, pad: int = 4) -> tuple[slice, slice]:
    rows, cols = np.nonzero(mask2d)
    return (slice(max(rows.min() - pad, 0), rows.max() + pad + 1),
            slice(max(cols.min() - pad, 0), cols.max() + pad + 1))


def show_mri(ax, sl: np.ndarray, m: np.ndarray) -> None:
    lo, hi = np.percentile(sl[m], [1, 99.5])
    ax.imshow(sl.T, cmap="gray", origin="lower", vmin=lo, vmax=hi, interpolation="nearest")
    ax.set_xticks([]); ax.set_yticks([])
    for sp in ax.spines.values():
        sp.set_visible(False)


def hist_panel(ax, v_gm: np.ndarray, v_wm: np.ndarray, lo: float, hi: float, xlabel: str,
               ovl_value: float) -> None:
    edges = np.linspace(lo, hi, N_BINS + 1)
    centers = 0.5 * (edges[:-1] + edges[1:])
    p_gm = np.histogram(v_gm, bins=edges)[0].astype(float)
    p_wm = np.histogram(v_wm, bins=edges)[0].astype(float)
    p_gm /= p_gm.sum()
    p_wm /= p_wm.sum()
    inter = np.minimum(p_gm, p_wm)

    ax.fill_between(centers, p_wm, step="mid", facecolor=COL_WM, edgecolor=EDGE_WM,
                    linewidth=0.9, linestyle="--", zorder=2)
    ax.fill_between(centers, p_gm, step="mid", facecolor=COL_GM, edgecolor=EDGE_GM,
                    linewidth=1.0, zorder=3)
    ax.fill_between(centers, inter, step="mid", facecolor="0.32", edgecolor="none", zorder=4)

    q = np.concatenate([v_gm, v_wm])
    ax.set_xlim(np.percentile(q, 0.2), np.percentile(q, 99.8))
    ax.set_ylim(0, max(p_gm.max(), p_wm.max()) * 1.28)
    ax.set_xlabel(xlabel)
    ax.set_yticks([])
    ax.text(0.03, 0.94, f"recouvrement = {ovl_value:.3f}", transform=ax.transAxes,
            ha="left", va="top", fontsize=8)
    for sp in ("top", "right", "left"):
        ax.spines[sp].set_visible(False)


def main() -> None:
    sid, meta = pick_subject()
    s = load_subject(sid, ROOT / "data")
    k = pick_slice(s.label)
    facts = meta["facts"]["per_subject"][str(sid)]

    sl_t1, sl_t2, sl_lb = s.t1[:, :, k], s.t2[:, :, k], s.label[:, :, k]
    m2d = s.mask[:, :, k]
    r, c = crop(m2d)
    sl_t1, sl_t2, sl_lb, m2d = sl_t1[r, c], sl_t2[r, c], sl_lb[r, c], m2d[r, c]

    fig = plt.figure(figsize=(6.4, 4.5))
    gs = fig.add_gridspec(2, 3, height_ratios=[1.18, 1.0], width_ratios=[1, 1, 1],
                          hspace=0.20, wspace=0.20,
                          left=0.055, right=0.99, top=0.955, bottom=0.10)

    for j, (sl, tag) in enumerate([(sl_t1, "(a) T1"), (sl_t2, "(b) T2")]):
        ax = fig.add_subplot(gs[0, j])
        show_mri(ax, sl, m2d)
        ax.set_title(tag, fontsize=8.5, pad=3)

    ax = fig.add_subplot(gs[0, 2])
    ax.imshow(sl_lb.T, cmap=ListedColormap(["white", COL_CSF, COL_GM, COL_WM]),
              origin="lower", vmin=0, vmax=3, interpolation="nearest")
    ax.set_xticks([]); ax.set_yticks([])
    for sp in ax.spines.values():
        sp.set_visible(False)
    ax.set_title("(c) segmentation de référence", fontsize=8.5, pad=3)

    lab_flat = s.label.reshape(-1)[np.flatnonzero(s.mask)]
    gm, wm = lab_flat == 2, lab_flat == 3
    for j, (vol, name) in enumerate([(s.t1, "T1"), (s.t2, "T2")]):
        v = vol[s.mask].astype(np.float64)
        ax = fig.add_subplot(gs[1, j])
        hist_panel(ax, v[gm], v[wm], float(v.min()), float(v.max()),
                   f"intensité {name} (u.a.)", facts[name])
        if j == 0:
            ax.set_ylabel("fréquence")
            ax.text(-0.14, 1.20, "(d)", transform=ax.transAxes, fontsize=8.5,
                    ha="left", va="top")

    ax = fig.add_subplot(gs[1, 2])
    ax.axis("off")
    ax.legend(handles=[
        Patch(facecolor=COL_CSF, edgecolor="0.35", linewidth=0.6, label=LABELS[1]),
        Patch(facecolor=COL_GM, edgecolor=EDGE_GM, linewidth=0.9, label=LABELS[2]),
        Patch(facecolor=COL_WM, edgecolor=EDGE_WM, linewidth=0.9, linestyle="--", label=LABELS[3]),
        Patch(facecolor="0.32", edgecolor="none", label="aire de recouvrement"),
    ], loc="center left", frameon=False, handlelength=1.6, handleheight=1.0,
        labelspacing=0.9, bbox_to_anchor=(-0.06, 0.55))

    out = ROOT / "report" / "assets" / "fig01_isointense.pdf"
    fig.savefig(out, format="pdf")
    print(f"{out}  sujet {sid}, coupe axiale {k}")
    print(f"  atypicité |z|max = {meta['atypicality'][sid]:.2f} "
          f"(min sur les 10 sujets) ; OVL T1 = {facts['T1']:.3f}, T2 = {facts['T2']:.3f}")


if __name__ == "__main__":
    main()
