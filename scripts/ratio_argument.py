"""Deux lectures du critère « Dice rapporté aux paramètres », et pourquoi l'une seule tient.

Le critère du hackathon met le Dice en regard du nombre de paramètres, sans dire comment. Deux
lectures sont possibles et elles ne donnent pas le même classement :

  RATIO BRUT      Dice / nombre de paramètres. Ne tient pas. Le Dice croît à peu près
                  logarithmiquement avec le nombre de paramètres, le dénominateur croît
                  linéairement : le quotient est donc systématiquement maximisé par le plus
                  petit modèle, quelle que soit sa qualité.

  ORDRE DE        On ne compare que la TRANCHE, c'est-à-dire la puissance de dix. Passer de 400
  GRANDEUR        à 700 paramètres ne change pas d'ordre de grandeur : les deux modèles sont
                  « à quelques centaines ». Le critère ne les départage donc pas, et c'est le
                  Dice qui tranche. Il ne dit quelque chose que lorsque la tranche change.

C'est la seconde lecture que le rapport retient. Elle est plus grossière, et c'est justement
ce qu'on lui demande : elle ne dépend pas d'une définition exacte de ce qui compte comme
paramètre appris, puisque tout désaccord raisonnable sur le comptage laisse la tranche
inchangée.

Le script calcule la tranche et le ratio brut de toutes nos configurations, plus un cas
dégénéré — un classifieur qui prédit partout le tissu majoritaire, majorité estimée sur les
9 sujets d'entraînement de chaque pli, et qui ne mémorise donc qu'un seul nombre.

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


def row(label: str, n_params: int, dice_mean: float) -> dict:
    """La tranche d'ordre de grandeur d'une configuration, et son ratio brut pour comparaison.

    `tranche` est floor(log10(p)) : deux modèles de même tranche sont « du même ordre de
    grandeur » et le critère retenu ne les départage pas. 400 et 700 paramètres sont tous deux
    dans la tranche 10^2 ; 1,55 million est dans la tranche 10^6.
    """
    return {
        "label": label,
        "n_params": n_params,
        "dice": dice_mean,
        "tranche": int(np.floor(np.log10(n_params))),
        "ratio": dice_mean / n_params,
    }


# Comptes de paramètres publiés du challenge, seules valeurs relevées sur une source primaire.
# Aucune méthode dont le décompte devrait être estimé n'entre ici ni dans le rapport.
PUBLISHED_TRANCHES = {
    6: "MSL_SKKU, 1,55 million (Wang et al. 2019)",
    7: "HyperDenseNet, 10 349 450 (Dolz et al. 2019, table 4)",
}

MOTS = {1: "une", 2: "deux", 3: "trois", 4: "quatre", 5: "cinq", 6: "six", 7: "sept"}


def ecart(t_ref: int, t_autre: int) -> str:
    """« deux tranches », « quatre à cinq tranches » : l'écart entre deux puissances de dix.

    Calculé, jamais écrit à la main : c'est exactement le genre de chiffre qu'une relecture
    laisse passer.
    """
    n = abs(t_autre - t_ref)
    return f"{MOTS[n]} tranche" + ("s" if n > 1 else "")


def spread(values: list[float]) -> float:
    """Facteur entre la plus grande et la plus petite valeur finie d'une colonne."""
    finite = [v for v in values if np.isfinite(v) and v > 0]
    return max(finite) / min(finite)


def main() -> None:
    rows = []
    for run, label in ORDER:
        f = ROOT / "results" / f"{run}.json"
        if not f.exists():
            continue
        r = json.loads(f.read_text())
        d = float(np.mean([v["dice_mean"] for v in r["per_subject"].values()]))
        rows.append(row(label, int(r["n_params"]), d))

    deg = degenerate_baseline()
    (ROOT / "results" / "degenerate_baseline.json").write_text(
        json.dumps(deg, indent=2, ensure_ascii=False))

    rows.append(row("classifieur dégénéré : tissu majoritaire partout", deg["n_params"], deg["dice_mean"]))
    rows.sort(key=lambda r: -r["ratio"])

    reels = [r for r in rows if r["n_params"] > 1]
    tranches = sorted({r["tranche"] for r in reels})
    meilleur_reel = max(reels, key=lambda r: r["dice"])
    t_nous, t_deg = tranches[0], int(np.floor(np.log10(deg["n_params"])))
    lines = [
        "<!-- généré par scripts/ratio_argument.py, ne pas éditer à la main -->",
        "",
        "# Les deux lectures du critère Dice / paramètres",
        "",
        "Classement par ratio brut décroissant. Le meilleur Dice est en gras.",
        "",
        "| rang | configuration | paramètres | tranche | Dice moyen | Dice / paramètres |",
        "|---:|---|---:|:---:|---:|---:|",
    ]
    best = max(r["dice"] for r in rows)
    for i, r in enumerate(rows, 1):
        d = f"**{r['dice']:.4f}**" if r["dice"] == best else f"{r['dice']:.4f}"
        lines.append(f"| {i} | {r['label']} | {r['n_params']} | $10^{{{r['tranche']}}}$ | {d} | {r['ratio']:.2e} |")
    lines += [
        "",
        f"Le classifieur dégénéré prédit partout la {list(deg['majority_class_per_fold'].values())[0]} "
        f"(majorité sur les 9 sujets d'entraînement, la même pour les 10 plis) et obtient un Dice "
        f"moyen de {deg['dice_mean']:.4f} ± {deg['dice_std']:.4f} pour un seul nombre mémorisé.",
        "",
        "## Ce que chaque lecture fait à nos configurations",
        "",
        f"Sur les {len(reels)} configurations réelles (le dégénéré exclu), le ratio brut s'étale "
        f"d'un facteur **{spread([r['ratio'] for r in reels]):.1f}**, alors que le Dice ne s'étale "
        f"que d'un facteur {spread([r['dice'] for r in reels]):.2f}. Le ratio brut mesure donc "
        "surtout la taille du modèle, et son classement est l'inverse du classement en Dice.",
        "",
        "En ordres de grandeur, le constat est d'une autre nature : "
        + (f"**nos {len(reels)} configurations sont TOUTES dans la même tranche, "
           f"$10^{{{tranches[0]}}}$**, de {min(r['n_params'] for r in reels)} à "
           f"{max(r['n_params'] for r in reels)} paramètres."
           if len(tranches) == 1 else
           f"nos configurations occupent les tranches {', '.join('$10^{%d}$' % t for t in tranches)}.")
        + " Cette lecture ne les départage donc pas, et n'a pas à le faire : à l'intérieur d'une "
        "tranche, c'est le Dice qui décide. Le meilleur est "
        f"« {meilleur_reel['label']} » à {meilleur_reel['dice']:.4f}.",
        "",
        "Cette lecture ne dit quelque chose que lorsque la tranche change. C'est le cas contre "
        "le challenge, dont les deux méthodes au décompte publié sont en "
        + " et ".join(f"$10^{{{t}}}$" for t in sorted(PUBLISHED_TRANCHES))
        + f", soit {MOTS[min(PUBLISHED_TRANCHES) - t_nous]} à "
        f"{ecart(t_nous, max(PUBLISHED_TRANCHES))} au-dessus. Et c'est le cas contre le "
        f"classifieur dégénéré, {ecart(t_nous, t_deg)} en dessous : son Dice de "
        f"{deg['dice_mean']:.2f} l'élimine immédiatement, ce qu'aucun ratio brut ne faisait.",
        "",
        "C'est la propriété qu'on demande à cette lecture : elle est trop grossière pour être "
        "abusée par une différence de comptage, et elle oblige à regarder le Dice partout où "
        "elle est muette.",
    ]
    (ROOT / "report" / "assets" / "ratio.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines[6:]))


if __name__ == "__main__":
    main()
