<!-- généré par scripts/ratio_argument.py, ne pas éditer à la main -->

# Le ratio brut Dice / paramètres, calculé sur nos configurations

Classement par ratio brut décroissant. Le meilleur Dice est en gras.

| rang | configuration | paramètres | Dice moyen | Dice / paramètres |
|---:|---|---:|---:|---:|
| 1 | classifieur dégénéré : tissu majoritaire partout | 1 | 0.2139 | 2.14e-01 |
| 2 | sélection des 40 meilleures colonnes | 163 | 0.8036 | 4.93e-03 |
| 3 | A+B+C, sans morphologie (référence) | 252 | 0.8055 | 3.20e-03 |
| 4 | palier 0 : max-tree + min-tree, nœud propre | 324 | 0.8156 | 2.52e-03 |
| 5 | palier 2 : arbre des formes + remontée de branche | 408 | 0.8154 | 2.00e-03 |
| 6 | palier 2, quantification sur 64 niveaux | 408 | 0.8149 | 2.00e-03 |
| 7 | palier 2, quantification par rang | 408 | 0.8136 | 1.99e-03 |
| 8 | palier 3 : palier 2 + filtres de grain | 426 | 0.8154 | 1.91e-03 |
| 9 | configuration finale : tous les blocs | 456 | 0.8276 | 1.81e-03 |
| 10 | configuration finale + lissage et nettoyage | 456 | 0.8246 | 1.81e-03 |
| 11 | configuration finale + lissage, nettoyage et contrainte topologique | 456 | 0.8235 | 1.81e-03 |
| 12 | palier 1 : max-tree + min-tree + remontée de branche | 564 | 0.8191 | 1.45e-03 |
| 13 | configuration finale + auto-contexte à deux étages | 939 | **0.8399** | 8.94e-04 |

Le classifieur dégénéré prédit partout la substance grise (majorité sur les 9 sujets d'entraînement, la même pour les 10 plis) et obtient un Dice moyen de 0.2139 ± 0.0082 pour un seul nombre mémorisé.
