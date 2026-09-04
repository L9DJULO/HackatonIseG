"""Pourquoi le ratio brut Dice / paramètres n'est pas une métrique de sélection.

L'argument se vérifie sur nos propres configurations et sur un cas dégénéré, il ne se
suppose pas. Deux calculs :

1. le ratio brut de chacune des configurations de results/, classées par ratio décroissant.
   Si la configuration la plus petite arrive en tête alors qu'elle est aussi la moins bonne
   en Dice, la métrique récompense la petitesse et non la qualité ;

2. le cas dégénéré : un classifieur qui prédit partout le tissu majoritaire, majorité
   estimée sur les 9 sujets d'entraînement de chaque pli. Il mémorise un seul nombre, un
   indice de classe. Son Dice moyen n'est pas nul, donc son ratio brut écrase tout le reste.

Usage : python scripts/ratio_argument.py -> results/degenerate_baseline.json + report/assets/ratio.md
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.eval.metrics import dice  # noqa: E402
from src.io import CLASS_NAMES, TISSUE_CLASSES, load_subject  # noqa: E402

FR = {"csf": "LCR", "gm": "substance grise", "wm": "substance blanche"}
from scripts.report_assets import ORDER  # noqa: E402


def degenerate_baseline() -> dict:
    """Leave-one-out : prédire partout le tissu majoritaire des 9 sujets d'entraînement."""
    subjects = {sid: load_subject(sid, ROOT / "data") for sid in range(1, 11)}
    counts = {sid: np.array([int((s.mask_labels == c).sum()) for c in TISSUE_CLASSES])
              for sid, s in subjects.items()}
    per_subject, chosen = {}, {}
    for sid, s in subjects.items():
        train = sum(counts[o] for o in subjects if o != sid)
        c = TISSUE_CLASSES[int(np.argmax(train))]
        chosen[sid] = FR[CLASS_NAMES[c]]
        gt = s.mask_labels
        # prédiction : TOUS les voxels du masque reçoivent la classe c
        d = {CLASS_NAMES[k]: dice(np.full(gt.shape, k == c, dtype=bool), gt == k)
             for k in TISSUE_CLASSES}
        per_subject[sid] = {**d, "mean": float(np.mean(list(d.values())))}
    means = np.array([per_subject[s]["mean"] for s in per_subject])
    return {
        "description": "prédit partout le tissu majoritaire des 9 sujets d'entraînement du pli",
        "majority_class_per_fold": chosen,
        "n_params": 1,
        "per_subject": per_subject,
        "dice_mean": float(means.mean()),
        "dice_std": float(means.std(ddof=1)),
    }


def main() -> None:
    rows = []
    for run, label in ORDER:
        f = ROOT / "results" / f"{run}.json"
        if not f.exists():
            continue
        r = json.loads(f.read_text())
        d = float(np.mean([v["dice_mean"] for v in r["per_subject"].values()]))
        rows.append({"label": label, "n_params": int(r["n_params"]), "dice": d,
                     "ratio": d / int(r["n_params"])})

    deg = degenerate_baseline()
    (ROOT / "results" / "degenerate_baseline.json").write_text(
        json.dumps(deg, indent=2, ensure_ascii=False))

    rows.append({"label": "classifieur dégénéré : tissu majoritaire partout",
                 "n_params": deg["n_params"], "dice": deg["dice_mean"],
                 "ratio": deg["dice_mean"] / deg["n_params"]})
    rows.sort(key=lambda r: -r["ratio"])

    lines = [
        "<!-- généré par scripts/ratio_argument.py, ne pas éditer à la main -->",
        "",
        "# Le ratio brut Dice / paramètres, calculé sur nos configurations",
        "",
        "Classement par ratio brut décroissant. Le meilleur Dice est en gras.",
        "",
        "| rang | configuration | paramètres | Dice moyen | Dice / paramètres |",
        "|---:|---|---:|---:|---:|",
    ]
    best = max(r["dice"] for r in rows)
    for i, r in enumerate(rows, 1):
        d = f"**{r['dice']:.4f}**" if r["dice"] == best else f"{r['dice']:.4f}"
        lines.append(f"| {i} | {r['label']} | {r['n_params']} | {d} | {r['ratio']:.2e} |")
    lines += [
        "",
        f"Le classifieur dégénéré prédit partout la {list(deg['majority_class_per_fold'].values())[0]} "
        f"(majorité sur les 9 sujets d'entraînement, la même pour les 10 plis) et obtient un Dice "
        f"moyen de {deg['dice_mean']:.4f} ± {deg['dice_std']:.4f} pour un seul nombre mémorisé.",
    ]
    (ROOT / "report" / "assets" / "ratio.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines[6:]))


if __name__ == "__main__":
    main()
