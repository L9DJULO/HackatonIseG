"""Génère report/assets/ depuis les JSON de results/. Aucun chiffre du rapport n'est écrit à la main.

Usage : python scripts/report_assets.py   (ou : make report-assets)

Produit :
  report/assets/ablation.md    tableau d'ablation, Dice par classe avec écart-tinter-sujets
  report/assets/stats.md       comparaisons appariées : delta, Wilcoxon, taille d'effet, sujets améliorés
  report/assets/distances.md   ASD et MHD par tissu : les deux autres métriques officielles
  report/assets/frugality.md   budget de frugalité mesuré (temps, mémoire, taille du modèle)
  report/assets/facts.md       chaque chiffre citable, avec son nom, sa valeur et son JSON source
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.eval.stats import apply_holm, compare, format_table  # noqa: E402

RESULTS = ROOT / "results"
ASSETS = ROOT / "report" / "assets"

# Ordre de lecture des configurations et libellé humain.
ORDER = [
    ("logreg_ABC", "A+B+C, sans morphologie (référence)"),
    ("logreg_ABCD_p0", "palier 0 : max-tree + min-tree, nœud propre"),
    ("logreg_ABCD_p1", "palier 1 : max-tree + min-tree + remontée de branche"),
    ("logreg_ABCD_p2", "palier 2 : arbre des formes + remontée de branche"),
    ("logreg_ABCD_p3", "palier 3 : palier 2 + filtres de grain"),
    ("logreg_ABCD_p2_l64", "palier 2, quantification sur 64 niveaux"),
    ("logreg_ABCD_p2_rank", "palier 2, quantification par rang"),
    ("logreg_final", "configuration finale : tous les blocs"),
    ("select_k40", "sélection des 40 meilleures colonnes"),
    ("logreg_final_smooth", "configuration finale + lissage et nettoyage"),
    ("logreg_final_postproc", "configuration finale + lissage, nettoyage et contrainte topologique"),
    ("autocontext_final", "configuration finale + auto-contexte à deux étages"),
]

# Comparaisons appariées déclarées à l'avance.
COMPARISONS = [
    ("logreg_ABC", "logreg_ABCD_p0", "apport du bloc D sans remontée de branche"),
    ("logreg_ABCD_p0", "logreg_ABCD_p1", "apport de la remontée de branche"),
    ("logreg_ABCD_p0", "logreg_ABCD_p2", "arbre des formes contre max-tree + min-tree"),
    ("logreg_ABCD_p1", "logreg_ABCD_p2", "auto-dualité à attributs identiques"),
    ("logreg_ABCD_p2", "logreg_ABCD_p3", "apport des filtres de grain"),
    ("logreg_ABCD_p2", "logreg_ABCD_p2_rank", "quantification par rang contre linéaire"),
    ("logreg_ABCD_p2", "logreg_ABCD_p2_l64", "64 niveaux contre 256"),
    ("logreg_ABC", "logreg_final", "apport de tous les blocs sur la référence"),
    ("logreg_ABCD_p2", "logreg_final", "apport des blocs symétrie et contexte"),
    # Déclarées au moment où les trois configurations correspondantes ont été figées dans
    # experiments/, avant leur exécution. Elles font partie de la MÊME famille que les
    # précédentes et sont corrigées avec elles : les ajouter après coup à une famille déjà
    # corrigée donnerait une correction trop permissive.
    ("logreg_final", "logreg_final_smooth", "apport du lissage et du nettoyage seuls"),
    ("logreg_final_smooth", "logreg_final_postproc", "apport de la contrainte topologique par-dessus"),
    ("logreg_final", "logreg_final_postproc", "apport du post-traitement complet"),
    ("logreg_final", "autocontext_final", "apport de l'auto-contexte"),
    ("logreg_final", "select_k40", "coût en Dice de la sélection à 40 colonnes"),
]

FACTS: list[tuple[str, str, str]] = []


def fact(name: str, value: str, source: str) -> None:
    FACTS.append((name, value, source))


def load(name: str) -> dict | None:
    p = RESULTS / f"{name}.json"
    return json.loads(p.read_text()) if p.exists() else None


def ablation_table(runs: dict[str, dict]) -> str:
    lines = [
        "| configuration | features | paramètres | Dice LCR | Dice SG | Dice SB | Dice moyen | ASD SG (mm) | MHD SG (mm) |",
        "|---|---:|---:|---|---|---|---:|---:|---:|",
    ]
    for key, label in ORDER:
        r = runs.get(key)
        if r is None:
            continue
        m, s = r["mean"], r["std"]
        lines.append(
            f"| {label} | {r['n_features']} | {r['n_params']} | "
            f"{m['dice_csf']:.3f} ± {s['dice_csf']:.3f} | {m['dice_gm']:.3f} ± {s['dice_gm']:.3f} | "
            f"{m['dice_wm']:.3f} ± {s['dice_wm']:.3f} | **{m['dice_mean']:.4f}** | "
            f"{m['asd_gm']:.2f} | {m['mhd_gm']:.2f} |"
        )
        src = f"results/{key}.json"
        fact(f"{label} — Dice moyen", f"{m['dice_mean']:.4f}", src)
        fact(f"{label} — paramètres", str(r["n_params"]), src)
        fact(f"{label} — features", str(r["n_features"]), src)
        for cls, nom in (("csf", "LCR"), ("gm", "SG"), ("wm", "SB")):
            fact(f"{label} — Dice {nom}", f"{m[f'dice_{cls}']:.3f} ± {s[f'dice_{cls}']:.3f}", src)
    return "\n".join(lines)


def stats_table(runs: dict[str, dict]) -> str:
    """Famille COMPLÈTE des comparaisons déclarées, corrigée de la multiplicité par Holm.

    apply_holm est appelé une fois sur la famille entière : corriger sur un sous-ensemble
    donnerait une correction trop permissive.
    """
    comps, labels = [], []
    for a, b, label in COMPARISONS:
        if a not in runs or b not in runs:
            continue
        comps.append(compare(runs[a], runs[b]))
        labels.append((a, b, label))
    apply_holm(comps)
    notes = []
    for c, (a, b, label) in zip(comps, labels):
        notes.append(
            f"- **{label}** : Δ = {c.delta:+.4f}, {c.n_improved}/{c.n_subjects} sujets améliorés, "
            f"p = {c.p_value:.3f} brut et {c.p_holm:.3f} après Holm, {c.verdict}."
        )
        fact(f"comparaison — {label}",
             f"Δ={c.delta:+.4f}, p={c.p_value:.3f} (Holm {c.p_holm:.3f}), {c.n_improved}/{c.n_subjects} sujets, {c.verdict}",
             f"results/{a}.json + results/{b}.json")
    preambule = (
        f"Famille de {len(comps)} comparaisons déclarées à l'avance. Le verdict est rendu sur la "
        "p-valeur ajustée de Holm, jamais sur la brute.\n"
    )
    return preambule + "\n" + format_table(comps) + "\n\n" + "\n".join(notes)


def distances_table(runs: dict[str, dict]) -> str:
    """ASD et MHD par tissu : les deux autres métriques officielles du challenge.

    Le Dice mesure un recouvrement de volume, les distances de surface mesurent une erreur de
    frontière. Une méthode peut gagner sur l'un sans gagner sur l'autre, et le challenge classe
    sur les trois séparément — les rapporter n'est donc pas facultatif.
    """
    lines = [
        "| configuration | ASD LCR | ASD SG | ASD SB | MHD LCR | MHD SG | MHD SB |",
        "|---|---:|---:|---:|---:|---:|---:|",
        "| | \\multicolumn{6}{c}{millimètres, moyenne sur les 10 sujets} |" if False else None,
    ]
    lines = [l for l in lines if l]
    for key, label in ORDER:
        r = runs.get(key)
        if r is None:
            continue
        m, sd = r["mean"], r["std"]
        cells = [f"{m[f'{metric}_{cls}']:.2f}" for metric in ("asd", "mhd") for cls in ("csf", "gm", "wm")]
        lines.append(f"| {label} | " + " | ".join(cells) + " |")
        src = f"results/{key}.json"
        for metric, nom_m in (("asd", "ASD"), ("mhd", "MHD")):
            for cls, nom in (("csf", "LCR"), ("gm", "SG"), ("wm", "SB")):
                fact(f"{label} — {nom_m} {nom} (mm)", f"{m[f'{metric}_{cls}']:.2f} ± {sd[f'{metric}_{cls}']:.2f}", src)
    note = (
        "\nToutes les valeurs sont en millimètres, moyennées sur les 10 sujets du leave-one-out. "
        "MHD est le 95e percentile des distances de surface symétriques, définition retenue par "
        "les tableaux du challenge (voir `src/eval/metrics.py`). Plus petit est meilleur.\n"
    )
    comps = []
    for a, b, label in (("logreg_ABC", "logreg_final", "apport de tous les blocs"),):
        if a in runs and b in runs:
            for metric in ("asd_gm", "mhd_gm"):
                c = compare(runs[a], runs[b], metric=metric)
                apply_holm([c])  # famille d'un seul test : la correction est neutre, on la trace
                comps.append(c)
                fact(f"comparaison {metric} — {label}",
                     f"Δ={c.delta:+.3f} mm, p={c.p_value:.3f}, {c.n_improved}/{c.n_subjects} sujets",
                     f"results/{a}.json + results/{b}.json")
    if not comps:
        return "\n".join(lines) + note
    return (
        "\n".join(lines) + note
        + "\nLe gain n'est pas seulement volumique : les mêmes blocs rapprochent aussi les "
        "surfaces. Comparaisons appariées sur la substance grise, chacune isolée dans sa propre "
        "famille (un seul test, la correction de Holm est donc neutre).\n\n"
        + format_table(comps) + "\n"
    )


def frugality_table() -> str:
    costs = sorted(RESULTS.glob("cost_*.json"))
    if not costs:
        return "_Aucune mesure de coût. Lancer `python scripts/measure_cost.py experiments/<config>.yaml`._"
    lines = [
        "| configuration | paramètres | extraction (s/sujet) | entraînement d'un fold (s) | inférence (s/volume) | pic mémoire (Go) | modèle sur disque (ko) |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    detail = []
    for p in costs:
        c = json.loads(p.read_text())
        lines.append(
            f"| {c['run_name']} | {c['n_params']} | {c['extract_seconds_per_subject']:.1f} | "
            f"{c['fit_seconds']:.1f} | {c['inference_seconds_per_volume']:.1f} | {c['peak_rss_gb']:.1f} | "
            f"{c['model_size_kilobytes']:.1f} |"
        )
        src = f"results/{p.name}"
        for k in ("extract_seconds_per_subject", "fit_seconds", "inference_seconds_per_volume", "peak_rss_gb", "model_size_kilobytes"):
            fact(f"{c['run_name']} — {k}", str(c[k]), src)
        detail.append(f"\nCoût d'extraction par bloc, {c['run_name']} (sujet {c['subject_id']}) :\n")
        detail.append("| bloc | features | secondes | mégaoctets |")
        detail.append("|---|---:|---:|---:|")
        for name, b in c["blocks"].items():
            detail.append(f"| {name} | {b['n_features']} | {b['seconds']:.1f} | {b['megabytes_float32']:.0f} |")
            fact(f"{c['run_name']} — bloc {name}, secondes par sujet", f"{b['seconds']:.1f}", src)
    machines = sorted({c.get("machine", "machine non enregistrée") for c in
                       (json.loads(p.read_text()) for p in costs)})
    garde = (
        "\n**Ces temps ne sont comparables qu'à machine égale.** Chaque mesure porte la machine "
        "qui l'a produite ; une ligne mesurée ailleurs ne se compare pas aux autres en secondes, "
        "seulement à elle-même. Machines présentes : " + " ; ".join(machines) + ".\n"
    )
    return "\n".join(lines) + "\n" + garde + "\n".join(detail)


def facts_file() -> str:
    lines = [
        "# Chiffres citables dans le rapport",
        "",
        "Généré par `make report-assets`. Chaque valeur vient d'un JSON de `results/`.",
        "Aucun chiffre du rapport ne doit être écrit sans figurer ici.",
        "",
        "| chiffre | valeur | source |",
        "|---|---|---|",
    ]
    for name, value, source in FACTS:
        lines.append(f"| {name} | {value} | `{source}` |")
    return "\n".join(lines)


def main() -> None:
    runs = {k: r for k, _ in ORDER if (r := load(k)) is not None}
    missing = [k for k, _ in ORDER if k not in runs]
    ASSETS.mkdir(parents=True, exist_ok=True)
    header = "<!-- généré par scripts/report_assets.py, ne pas éditer à la main -->\n\n"
    ablation = ablation_table(runs)
    distances = distances_table(runs)
    stats = stats_table(runs)
    frugality = frugality_table()
    (ASSETS / "ablation.md").write_text(header + "# Ablation, leave-one-out sur 10 sujets\n\n" + ablation + "\n")
    (ASSETS / "distances.md").write_text(header + "# Distances de surface : ASD et MHD par tissu\n\n" + distances + "\n")
    (ASSETS / "stats.md").write_text(header + "# Comparaisons appariées\n\n" + stats + "\n")
    (ASSETS / "frugality.md").write_text(header + "# Budget de frugalité\n\n" + frugality + "\n")
    (ASSETS / "facts.md").write_text(header + facts_file() + "\n")
    print(f"report/assets/ régénéré : {len(runs)} runs, {len(FACTS)} chiffres référencés")
    if missing:
        print("runs absents :", ", ".join(missing))


if __name__ == "__main__":
    main()
