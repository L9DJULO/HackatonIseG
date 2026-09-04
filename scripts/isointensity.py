"""Mesure du recouvrement des distributions d'intensité substance grise / substance blanche.

C'est le chiffre qui justifie tout le rapport : à 6 mois, la myélinisation est à mi-course
et les deux tissus ont presque la même intensité. On le mesure, on ne le suppose pas.

DÉFINITION (celle qui doit figurer dans le texte) — coefficient de recouvrement OVL :

    OVL = somme_b min( p_SG(b), p_SB(b) )

où p_SG et p_SB sont les histogrammes normalisés (de somme 1) des intensités de la substance
grise et de la substance blanche, calculés sur les mêmes 256 classes réparties linéairement
sur l'étendue des intensités intra-masque du sujet et de la modalité considérés. OVL vaut 0
pour deux distributions disjointes et 1 pour deux distributions identiques. Les 256 classes
sont le même pas de quantification que celui du bloc morphologique.

Conséquence directe, et c'est elle qui compte : à effectifs égaux, la meilleure règle de
décision possible fondée sur la SEULE intensité d'un voxel se trompe sur OVL/2 des voxels.
Un OVL de 0.80 plafonne donc l'exactitude d'une telle règle à 60 %.

Quatre signaux sont mesurés avec le même estimateur : T1 brut, T2 brut, le ratio normalisé
du bloc A — (T1/med T1 - T2/med T2) rapporté à leur somme — et le couple (T1, T2) sur une
grille 64 x 64.

Un OVL empirique est biaisé vers le bas : même pour deux distributions identiques, deux
histogrammes finis ne se superposent pas exactement, et le biais croît avec le nombre de
classes. On mesure donc pour chaque signal un PLAFOND : l'OVL entre deux moitiés tirées au
hasard des seuls voxels de substance grise, dont la valeur vraie est 1. L'écart au plafond
est ce qui est réellement interprétable, et il rend les dimensions comparables entre elles.

Usage : python scripts/isointensity.py  ->  results/isointensity.json + report/assets/isointensity.md
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.io import load_subject  # noqa: E402

N_BINS = 256
N_BINS_2D = 64
SEED = 0
JOINT = "couple (T1, T2)"
SIGNALS = ("T1", "T2", "ratio T1/T2", JOINT)
SUBJECTS = range(1, 11)
GM, WM = 2, 3


def ovl(a: np.ndarray, b: np.ndarray, lo: float, hi: float, n_bins: int = N_BINS) -> float:
    """Coefficient de recouvrement de deux échantillons, sur un binning commun imposé."""
    edges = np.linspace(lo, hi, n_bins + 1)
    pa, _ = np.histogram(a, bins=edges)
    pb, _ = np.histogram(b, bins=edges)
    pa = pa / pa.sum()
    pb = pb / pb.sum()
    return float(np.minimum(pa, pb).sum())


def ovl_2d(a: np.ndarray, b: np.ndarray, rng_lo, rng_hi, n_bins: int = N_BINS_2D) -> float:
    """Même coefficient, sur la loi jointe (T1, T2) discrétisée sur une grille n_bins x n_bins."""
    edges = [np.linspace(rng_lo[i], rng_hi[i], n_bins + 1) for i in (0, 1)]
    pa, _, _ = np.histogram2d(a[:, 0], a[:, 1], bins=edges)
    pb, _, _ = np.histogram2d(b[:, 0], b[:, 1], bins=edges)
    return float(np.minimum(pa / pa.sum(), pb / pb.sum()).sum())


def signals(subject) -> dict[str, np.ndarray]:
    """Les trois signaux comparés, tous restreints au masque, dans le même ordre de voxels."""
    m = subject.mask
    t1 = subject.t1[m].astype(np.float64)
    t2 = subject.t2[m].astype(np.float64)
    t1_n = t1 / (np.median(t1) + 1e-6)
    t2_n = t2 / (np.median(t2) + 1e-6)
    ratio = (t1_n - t2_n) / (t1_n + t2_n + 1e-3)
    return {"T1": t1, "T2": t2, "ratio T1/T2": ratio}, np.stack([t1, t2], axis=1)


def main() -> None:
    per_subject: dict[str, dict[str, float]] = {}
    for sid in SUBJECTS:
        s = load_subject(sid, ROOT / "data")
        lab = s.label.reshape(-1)[np.flatnonzero(s.mask)]
        gm, wm = lab == GM, lab == WM
        rng = np.random.default_rng(SEED + sid)
        half = rng.permutation(int(gm.sum())) < int(gm.sum()) // 2  # partition des voxels SG
        sig1d, joint = signals(s)
        row = {}
        for name, v in sig1d.items():
            lo, hi = float(v.min()), float(v.max())
            row[name] = ovl(v[gm], v[wm], lo, hi)
            g = v[gm]
            row[name + " (plafond)"] = ovl(g[half], g[~half], lo, hi)
        lo = joint.min(axis=0)
        hi = joint.max(axis=0)
        row[JOINT] = ovl_2d(joint[gm], joint[wm], lo, hi)
        g = joint[gm]
        row[JOINT + " (plafond)"] = ovl_2d(g[half], g[~half], lo, hi)
        row["n_gm"] = int(gm.sum())
        row["n_wm"] = int(wm.sum())
        per_subject[str(sid)] = row
        print(f"subject-{sid:<2d} " + "  ".join(f"{k}={row[k]:.4f}" for k in SIGNALS))

    summary = {}
    for name in SIGNALS:
        vals = np.array([per_subject[str(s)][name] for s in SUBJECTS])
        ceil = np.array([per_subject[str(s)][name + " (plafond)"] for s in SUBJECTS])
        summary[name] = {
            "mean": float(vals.mean()),
            "std": float(vals.std(ddof=1)),
            "min": float(vals.min()),
            "max": float(vals.max()),
            "median": float(np.median(vals)),
            "ceiling_mean": float(ceil.mean()),
            "ceiling_std": float(ceil.std(ddof=1)),
            "gap_to_ceiling_mean": float((ceil - vals).mean()),
            "bayes_error_max": float(vals.mean() / 2),
        }

    out = {
        "definition": "OVL = sum_b min(p_GM(b), p_WM(b)), 256 classes linéaires sur l'étendue "
                      "intra-masque du sujet et de la modalité",
        "n_bins": N_BINS,
        "subjects": sorted(SUBJECTS),
        "per_subject": per_subject,
        "summary": summary,
    }
    (ROOT / "results" / "isointensity.json").write_text(json.dumps(out, indent=2, ensure_ascii=False))

    lines = [
        "<!-- généré par scripts/isointensity.py, ne pas éditer à la main -->",
        "",
        "# Recouvrement des distributions substance grise / substance blanche",
        "",
        f"OVL = somme des minima de deux histogrammes normalisés à {N_BINS} classes, sur l'étendue",
        "intra-masque du sujet et de la modalité. 0 = disjoint, 1 = identique.",
        "Moyenne et écart-type sur les 10 sujets annotés.",
        "",
        "| signal | OVL moyen | écart-type | min | max | plafond de l'estimateur | écart au plafond | exactitude maximale d'une décision par voxel |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for name in SIGNALS:
        d = summary[name]
        lines.append(
            f"| {name} | {d['mean']:.3f} | {d['std']:.3f} | {d['min']:.3f} | {d['max']:.3f} | "
            f"{d['ceiling_mean']:.3f} | {d['gap_to_ceiling_mean']:.3f} | "
            f"{100 * (1 - d['bayes_error_max']):.1f} % |"
        )
    lines += ["", "Détail par sujet :", "",
              "| sujet | OVL T1 | OVL T2 | OVL ratio | OVL couple (T1, T2) |", "|---|---:|---:|---:|---:|"]
    for sid in SUBJECTS:
        r = per_subject[str(sid)]
        lines.append(f"| {sid} | {r['T1']:.3f} | {r['T2']:.3f} | {r['ratio T1/T2']:.3f} | {r[JOINT]:.3f} |")
    (ROOT / "report" / "assets" / "isointensity.md").write_text("\n".join(lines) + "\n")
    print("\n" + "\n".join(lines[7:15]))


if __name__ == "__main__":
    main()
