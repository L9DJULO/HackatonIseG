<!-- généré par scripts/ratio_argument.py, ne pas éditer à la main -->

# Les deux lectures du critère Dice / paramètres

Classement par ratio brut décroissant. Le meilleur Dice est en gras.

| rang | configuration | paramètres | tranche | Dice moyen | Dice / paramètres |
|---:|---|---:|:---:|---:|---:|
| 1 | classifieur dégénéré : tissu majoritaire partout | 1 | $10^{0}$ | 0.2139 | 2.14e-01 |
| 2 | sélection des 40 meilleures colonnes | 163 | $10^{2}$ | 0.8036 | 4.93e-03 |
| 3 | A+B+C, sans morphologie (référence) | 252 | $10^{2}$ | 0.8055 | 3.20e-03 |
| 4 | palier 0 : max-tree + min-tree, nœud propre | 324 | $10^{2}$ | 0.8156 | 2.52e-03 |
| 5 | palier 2 : arbre des formes + remontée de branche | 408 | $10^{2}$ | 0.8154 | 2.00e-03 |
| 6 | palier 2, quantification sur 64 niveaux | 408 | $10^{2}$ | 0.8149 | 2.00e-03 |
| 7 | palier 2, quantification par rang | 408 | $10^{2}$ | 0.8136 | 1.99e-03 |
| 8 | palier 3 : palier 2 + filtres de grain | 426 | $10^{2}$ | 0.8154 | 1.91e-03 |
| 9 | configuration finale : tous les blocs | 456 | $10^{2}$ | 0.8276 | 1.81e-03 |
| 10 | configuration finale + lissage et nettoyage | 456 | $10^{2}$ | 0.8246 | 1.81e-03 |
| 11 | configuration finale + lissage, nettoyage et contrainte topologique | 456 | $10^{2}$ | 0.8235 | 1.81e-03 |
| 12 | palier 1 : max-tree + min-tree + remontée de branche | 564 | $10^{2}$ | 0.8191 | 1.45e-03 |
| 13 | configuration finale + auto-contexte à deux étages | 939 | $10^{2}$ | **0.8399** | 8.94e-04 |

Le classifieur dégénéré prédit partout la substance grise (majorité sur les 9 sujets d'entraînement, la même pour les 10 plis) et obtient un Dice moyen de 0.2139 ± 0.0082 pour un seul nombre mémorisé.

## Ce que chaque lecture fait à nos configurations

Sur les 12 configurations réelles (le dégénéré exclu), le ratio brut s'étale d'un facteur **5.5**, alors que le Dice ne s'étale que d'un facteur 1.05. Le ratio brut mesure donc surtout la taille du modèle, et son classement est l'inverse du classement en Dice.

En ordres de grandeur, le constat est d'une autre nature : **nos 12 configurations sont TOUTES dans la même tranche, $10^{2}$**, de 163 à 939 paramètres. Cette lecture ne les départage donc pas, et n'a pas à le faire : à l'intérieur d'une tranche, c'est le Dice qui décide. Le meilleur est « configuration finale + auto-contexte à deux étages » à 0.8399.

Cette lecture ne dit quelque chose que lorsque la tranche change. C'est le cas contre le challenge, dont les deux méthodes au décompte publié sont en $10^{6}$ et $10^{7}$, soit quatre à cinq tranches au-dessus. Et c'est le cas contre le classifieur dégénéré, deux tranches en dessous : son Dice de 0.21 l'élimine immédiatement, ce qu'aucun ratio brut ne faisait.

C'est la propriété qu'on demande à cette lecture : elle est trop grossière pour être abusée par une différence de comptage, et elle oblige à regarder le Dice partout où elle est muette.
