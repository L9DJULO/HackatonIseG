from pathlib import Path
import re
root = Path(__file__).resolve().parents[1]
p = root / 'scripts/report_assets.py'
s = p.read_text(encoding='utf-8')
s = s.replace('Test contre leave-one-out, même modèle', 'Test contre leave-one-out, même configuration réentraînée')
a = s.index('        "L\'écart est positif sur les trois tissus.')
b = s.index('    return "\\n".join(lines)', a)
s = s[:a] + '''        "L'écart est positif sur les trois tissus. Les sujets et les effectifs d'entraînement "
        "diffèrent : ce constat ne démontre ni l'absence de fuite ni un biais conservateur.",
        "",
        "Les distances locales et officielles restent séparées. L'article du challenge décrit "
        "HD95, mais l'équivalence des implémentations n'a pas été vérifiée. Des valeurs différentes "
        "sur deux populations ne suffisent pas à démontrer des définitions différentes.",
    ]
''' + s[b:]
s = s.replace('Chaque valeur vient d\'un JSON de `results/`.', 'Sources : JSON de `results/`, classeur officiel et références publiées sourcées.')
s = s.replace('    test_results = test_results_table(runs)', '''    test_results = test_results_table(runs)
    published = json.loads((RESULTS / "published_references.json").read_text(encoding="utf-8"))
    for name, vals in published["methods"].items():
        for key, value in vals.items():
            if isinstance(value, (int, float)):
                fact(f"{name} — {key}", str(value), "results/published_references.json")
        fact(f"{name} — Dice moyen publié", f"{sum(vals[f'dice_{t}'] for t in TISSUES)/3:.4f}", published["score_source"])
    if (RESULTS / XLSX_NAME).exists():
        sc = load_official_scores(RESULTS / XLSX_NAME)
        ref = published["methods"]["MSL_SKKU"]
        dm = sum(ref[f"dice_{t}"] for t in TISSUES) / 3
        fact("Test — pourcentage du Dice de MSL_SKKU", f"{100*sc['dice_mean']/dm:.1f}", "classeur officiel + published_references.json")
        for t in TISSUES:
            fact(f"Test — pourcentage du Dice MSL_SKKU {FR[t]}", f"{100*sc['mean'][f'dice_{t}']/ref[f'dice_{t}']:.1f}", "classeur officiel + published_references.json")
    fact("Sélection — paramètres économisés", "293", "456 - 163")
    fact("Sélection — réduction en pourcentage", f"{100*(456-163)/456:.1f}", "logreg_final.json + select_k40.json")
    fact("Auto-contexte — convention alternative", "1241", "939 + 2*151")
    sub = json.loads((RESULTS / "submission.json").read_text(encoding="utf-8"))
    fact("Soumission — entraînement en secondes", str(sub["fit_seconds"]), "results/submission.json")
    fact("Soumission — secondes moyennes par sujet", str(sub["mean_seconds_per_test_subject"]), "results/submission.json")
    frugality += ("\\n\\n## Chaîne soumise à auto-contexte\\n\\n"
        f"Entraînement final : {sub['fit_seconds']} s ; temps moyen par sujet de test : "
        f"{sub['mean_seconds_per_test_subject']} s. Source : `results/submission.json`. "
        "Pic mémoire et taille du modèle sur disque non enregistrés pour cette chaîne.\\n")''')
# Every generated text file is explicitly UTF-8, including on Windows.
s = re.sub(r'\.write_text\((header[^\n]*?)\)', r'.write_text(\1, encoding="utf-8")', s)
s = s.replace('+ test_results + "\\n")', '+ test_results + "\\n", encoding="utf-8")')
p.write_text(s, encoding='utf-8')

p = root / 'src/eval/official.py'
s = p.read_text(encoding='utf-8')
a = s.index('ATTENTION AUX MÉTRIQUES')
b = s.index('Le classeur place', a)
s = s[:a] + '''DISTANCES. L'article du challenge décrit HD95. L'équivalence exacte avec notre
implémentation n'a pas été vérifiée. Un rapport entre agrégats de deux jeux différents
ne prouve pas que les définitions sont différentes et n'identifie pas la cause des erreurs.

''' + s[b:]
a = s.index('    """{tissu -> MHD serveur')
b = s.index('    return {t:', a)
s = s[:a] + '    """Rapport descriptif entre deux populations, sans conclusion sur les définitions."""\n' + s[b:]
p.write_text(s, encoding='utf-8')

p = root / 'tests/test_official.py'
s = p.read_text(encoding='utf-8')
a = s.index('def test_les_deux_mhd')
s = s[:a] + '''def test_agregats_par_tissu_sur_une_ligne_connue(scores):
    # Lecture indépendante de la ligne du sujet 11 : évite de valider un appariement
    # de colonnes erroné en réutilisant la carte de colonnes du parseur.
    import openpyxl
    ws = openpyxl.load_workbook(XLSX, data_only=True)["Sheet1"]
    rows = list(ws.iter_rows(values_only=True))
    row = next(r for r in rows if len(r) >= 22 and str(r[10]).strip() == "11")
    for tissue, start in (("csf", 13), ("gm", 16), ("wm", 19)):
        for metric, offset in (("dice", 0), ("mhd", 1), ("asd", 2)):
            assert scores["per_subject"][11][f"{metric}_{tissue}"] == float(row[start+offset])
'''
p.write_text(s, encoding='utf-8')

p = root / 'report/rapport.md'
s = p.read_text(encoding='utf-8').replace('Le code interne utilise une ASD symétrique et un 95',
    'Le code interne mesure les distances des voxels de frontière au masque de l’autre tissu\n(prédiction vers référence et réciproquement), puis une moyenne et un 95')
p.write_text(s, encoding='utf-8')

p = root / 'report/refs.bib'
s = p.read_text(encoding='utf-8').replace('98--110', '97--108')
# Remove stale self-certification comments; the final review lists checked sources.
s = s[s.index('@article'):]
s = s.split('% ===========================================================================')[0]
p.write_text(s, encoding='utf-8')
