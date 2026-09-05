# iseg-frugal

Segmentation LCR / substance grise / substance blanche sur les IRM T1 et T2 de nourrissons de
6 mois du challenge MICCAI iSeg-2017, avec des descripteurs **non appris** et un classifieur
**minuscule**. Le pipeline entier tient dans 456 paramètres appris.

## Reproduire le résultat principal

```bash
make venv                                    # environnement et dépendances épinglées
ln -s ../iSeg-2017-Training data/train ; ln -s ../iSeg-2017-Testing data/test
python -m src.cli run experiments/logreg_final.yaml
```

Une commande, un JSON dans `results/`. `make test` lance la suite de tests, `make grid` toute la
grille d'ablation, `make report-assets` régénère les tableaux du rapport depuis les JSON.

## Résultat

Leave-one-out sur les 10 sujets annotés, régression logistique, 5 000 voxels par tissu et par
sujet, correction des priors. Dice moyen par sujet, jamais agrégé sur les voxels.

| | Dice LCR | Dice SG | Dice SB | Dice moyen | paramètres |
|---|---|---|---|---:|---:|
| sans morphologie | 0.851 ± 0.015 | 0.805 ± 0.011 | 0.761 ± 0.017 | 0.8055 | 252 |
| configuration finale | 0.881 ± 0.014 | 0.825 ± 0.009 | 0.777 ± 0.017 | **0.8276** | **456** |

Les tableaux complets, les comparaisons appariées et le budget de coût sont dans
`report/assets/`, régénérés depuis les JSON. Aucun chiffre du rapport n'est écrit à la main.

## Comment lire le nombre de paramètres

Le critère du projet met le Dice en regard du nombre de paramètres. Ce rapport ne doit **jamais**
être présenté comme un ratio à maximiser : un ratio Dice sur paramètres est toujours maximisé par
le modèle le plus petit, et il désignerait vainqueur un modèle qui prédit la classe majoritaire.
Le cadrage correct est le front de Pareto, et la comparaison d'ordre de grandeur avec les méthodes
publiées du challenge : la méthode classée première en compte 1,55 · 10⁶ (chiffre publié dans
l'article de synthèse du challenge), et les architectures des autres participations situent
l'ensemble entre 10⁶ et 10⁸, là où nous en avons quelques centaines.

La convention de comptage est écrite dans `src/models/params.py` : comptent les quantités ajustées
sur les sujets d'entraînement et transportées à l'inférence ; ne comptent pas celles recalculées
sur le sujet courant, comme la standardisation intra-masque. La zone grise est assumée et chiffrée.

## Blocs de features

Tous à zéro paramètre appris, ce que la suite de tests vérifie mécaniquement : les features sont
identiques avec le vrai label, un label permuté, ou aucun label.

| bloc | n | contenu |
|---|---:|---|
| intensity | 6 | T1 et T2 z-scorés dans le masque, ratio des intensités normalisées par la médiane, rangs percentiles |
| gaussian | 68 | σ ∈ {0.5, 1, 2, 4, 8} mm × {T1, T2} : lissage, norme du gradient, laplacien, valeurs propres de la Hessienne triées, différences de gaussiennes, convolution normalisée au bord du masque |
| spatial | 9 | coordonnées normalisées, distance au bord du masque, distance au plan sagittal médian estimé par ACP, coordonnées sphériques |
| morpho | 52 | arbre des formes 3D auto-dual : attributs de la plus petite forme contenant le voxel, puis remontée de branche vers les ancêtres de volume ≥ 100, 1 000, 10 000 et 100 000 voxels |
| symmetry | 4 | intensité au point miroir par rapport au plan sagittal médian, et écart au miroir |
| context | 12 | moyenne et écart-type locaux des rangs percentiles, rayons 1, 2 et 4 voxels |

Les hyperparamètres fixés a priori sont listés dans le docstring de chaque bloc et recopiés dans
chaque JSON sous `feature_config`.

## Structure

```
src/io.py              chargement Analyze 7.5 ; masque = T1 non nul, identique à label non nul
src/features/          interface, cache disque, standardisation intra-sujet, 6 blocs
src/sampling.py        tirage équilibré, frontière, correction des priors
src/eval/              métriques Dice / ASD / MHD, boucle leave-one-out, statistiques appariées
src/models/params.py   convention de comptage des paramètres
src/cli.py             run / features / blocks
experiments/*.yaml     une configuration par run     results/*.json  un résultat par run
```

## Limites connues

- Dix sujets seulement : les écarts inférieurs à 0.005 de Dice ne sont pas distinguables du bruit,
  et `report/assets/stats.md` dit lesquels le sont.
- Les hyperparamètres des blocs sont fixés a priori, pas validés dans le fold. Ils ne sont pas
  ajustés sur les données, mais un jury peut objecter qu'ils incorporent une connaissance du
  domaine acquise ailleurs.
- La quantification linéaire du bloc morphologique fait perdre l'invariance à toute transformation
  croissante de l'intensité ; seule l'invariance affine subsiste. Le choix se défend parce que les
  volumes sont déjà corrigés en inhomogénéité de champ, et l'écart mesuré avec la variante
  invariante n'est pas significatif.
- L'optimiseur de la régression logistique est arrêté à 300 itérations alors qu'il en demande 319
  pour converger complètement. L'écart a été mesuré sur un fold : Dice identique à la quatrième
  décimale, norme des poids 10.19 contre 10.33. Les chiffres publiés ne sont pas affectés.
- Les 13 sujets de test du challenge n'ont pas de vérité terrain publique : ils ne servent qu'à des
  figures qualitatives.
