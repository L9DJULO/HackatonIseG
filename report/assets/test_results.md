<!-- généré par scripts/report_assets.py, ne pas éditer à la main -->

# Scores officiels du serveur iSeg-2017, 13 sujets de test

Modèle soumis : `autocontext_final`, 939 paramètres appris, entraîné sur les 10 sujets annotés d'un coup (et non sur les 9 d'un pli), puis appliqué aux 13 sujets de test. Source : `results/submission.json`.

## Scores rendus par le serveur

| tissu | Dice | ASD (mm) | MHD (mm) |
|---|---|---|---|
| LCR | 0.8992 ± 0.0111 | 0.297 ± 0.031 | 10.77 ± 0.94 |
| SG | 0.8375 ± 0.0124 | 0.614 ± 0.041 | 8.30 ± 1.46 |
| SB | 0.7968 ± 0.0194 | 0.798 ± 0.065 | 12.77 ± 2.07 |
| **moyenne des trois** | **0.8445** | | |

Dice moyen par sujet, du meilleur au pire : 13 (0.8600), 16 (0.8541), 11 (0.8537), 21 (0.8513), 19 (0.8511), 15 (0.8491), 18 (0.8464), 14 (0.8451), 17 (0.8439), 23 (0.8429), 22 (0.8346), 12 (0.8240), 20 (0.8226).

## Test contre leave-one-out, même configuration réentraînée

| Dice | leave-one-out (10 sujets) | test officiel (13 sujets) | écart |
|---|---:|---:|---:|
| LCR | 0.8913 | 0.8992 | +0.0079 |
| SG | 0.8336 | 0.8375 | +0.0038 |
| SB | 0.7946 | 0.7968 | +0.0022 |
| moyen | 0.8399 | 0.8445 | **+0.0047** |

L'écart est positif sur les trois tissus. Les sujets et les effectifs d'entraînement diffèrent : ce constat ne démontre ni l'absence de fuite ni un biais conservateur.

Les distances locales et officielles restent séparées. L'article du challenge décrit HD95, mais l'équivalence des implémentations n'a pas été vérifiée. Des valeurs différentes sur deux populations ne suffisent pas à démontrer des définitions différentes.
