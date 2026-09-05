<!-- généré par scripts/report_assets.py, ne pas éditer à la main -->

# Budget de frugalité

| configuration | paramètres | extraction (s/sujet) | entraînement d'un fold (s) | inférence (s/volume) | pic mémoire (Go) | modèle sur disque (ko) |
|---|---:|---:|---:|---:|---:|---:|
| logreg_ABC | 252 | 19.1 | 44.2 | 1.0 | 1.6 | 1.7 |
| logreg_ABCD_p2 | 408 | 83.1 | 31.7 | 3.7 | 2.1 | 3.9 |
| logreg_ABCD_p2_l64 | 408 | 87.8 | 34.8 | 4.4 | 2.1 | 3.9 |
| logreg_final | 456 | 44.5 | 63.3 | 1.3 | 3.3 | 2.5 |

**Ces temps ne sont comparables qu'à machine égale.** Chaque mesure porte la machine qui l'a produite ; une ligne mesurée ailleurs ne se compare pas aux autres en secondes, seulement à elle-même. Machines présentes : machine non enregistrée ; vm / x86_64 / python 3.11.15.

Coût d'extraction par bloc, logreg_ABC (sujet 1) :

| bloc | features | secondes | mégaoctets |
|---|---:|---:|---:|
| intensity | 6 | 0.3 | 22 |
| gaussian | 68 | 17.2 | 251 |
| spatial | 9 | 1.7 | 33 |

Coût d'extraction par bloc, logreg_ABCD_p2 (sujet 1) :

| bloc | features | secondes | mégaoctets |
|---|---:|---:|---:|
| intensity | 6 | 0.9 | 22 |
| gaussian | 68 | 35.1 | 251 |
| spatial | 9 | 2.6 | 33 |
| morpho | 52 | 44.5 | 192 |

Coût d'extraction par bloc, logreg_ABCD_p2_l64 (sujet 1) :

| bloc | features | secondes | mégaoctets |
|---|---:|---:|---:|
| intensity | 6 | 0.4 | 22 |
| gaussian | 68 | 36.7 | 251 |
| spatial | 9 | 3.0 | 33 |
| morpho | 52 | 47.7 | 192 |

Coût d'extraction par bloc, logreg_final (sujet 1) :

| bloc | features | secondes | mégaoctets |
|---|---:|---:|---:|
| intensity | 6 | 0.3 | 22 |
| gaussian | 68 | 17.8 | 251 |
| spatial | 9 | 1.8 | 33 |
| morpho | 52 | 23.5 | 192 |
| symmetry | 4 | 0.5 | 15 |
| context | 12 | 0.7 | 44 |

## Chaîne soumise à auto-contexte

Entraînement final : 320.1 s ; temps moyen par sujet de test : 86.7 s. Source : `results/submission.json`. Pic mémoire et taille du modèle sur disque non enregistrés pour cette chaîne.
