<!-- généré par scripts/report_assets.py, ne pas éditer à la main -->

# Budget de frugalité

| configuration | paramètres | extraction (s/sujet) | entraînement d'un fold (s) | inférence (s/volume) | pic mémoire (Go) | modèle sur disque (ko) |
|---|---:|---:|---:|---:|---:|---:|
| logreg_ABC | 252 | 19.1 | 44.2 | 1.0 | 1.6 | 1.7 |
| logreg_final | 456 | 44.5 | 63.3 | 1.3 | 3.3 | 2.5 |

Coût d'extraction par bloc, logreg_ABC (sujet 1) :

| bloc | features | secondes | mégaoctets |
|---|---:|---:|---:|
| intensity | 6 | 0.3 | 22 |
| gaussian | 68 | 17.2 | 251 |
| spatial | 9 | 1.7 | 33 |

Coût d'extraction par bloc, logreg_final (sujet 1) :

| bloc | features | secondes | mégaoctets |
|---|---:|---:|---:|
| intensity | 6 | 0.3 | 22 |
| gaussian | 68 | 17.8 | 251 |
| spatial | 9 | 1.8 | 33 |
| morpho | 52 | 23.5 | 192 |
| symmetry | 4 | 0.5 | 15 |
| context | 12 | 0.7 | 44 |
