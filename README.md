# iseg-frugal — Hackathon SCIA 2026, sujet iSeg-2017

Segmentation LCR / SG / SB de cerveaux de nourrissons de 6 mois (IRM T1+T2) avec des
descripteurs **non appris** (0 paramètre) et un classifieur **minuscule**. Critère du jury :
Dice rapporté au nombre de paramètres, et originalité.

## Installation

```bash
make venv                      # crée .venv et installe requirements.txt
ln -s ../iSeg-2017-Training data/train ; ln -s ../iSeg-2017-Testing data/test
make test                      # tests unitaires (métriques, blocs, sampling, io)
make inspect                   # vérification brute des données
```

## Reproduire un résultat

```bash
python -m src.cli run experiments/logreg_ABCD.yaml       # LOO 10 folds -> results/logreg_ABCD.json
python -m src.cli features experiments/logreg_ABCDEF.yaml # ne fait que remplir le cache
python -m src.cli blocks                                  # liste les blocs et leurs colonnes
make grid                                                 # toute la grille experiments/logreg_*.yaml (~1 h)
make table                                                # tableau markdown depuis results/*.json
make figures                                              # coupe axiale des features (figures/)
```

Un YAML décrit tout : blocs de features, modèle, échantillonnage, post-traitement, seed.
Les features sont calculées une fois par sujet et par bloc, mises en cache dans `cache/`
(memmap `.npy`, clé = nom du bloc + hash de sa config) ; jamais recalculées à l'entraînement.
Les probabilités prédites de chaque fold sont dans `results/proba/<run>/subject-k.npz`
(`proba` float16 (n_mask, 3) dans l'ordre `np.flatnonzero(mask)`, `mask` bool), reconstruites
en volume avec `src.io.mask_to_volume`.

Échantillonnage : `n_per_class` voxels par tissu et par sujet, tirage équilibré (option
`boundary_frac` pour sur-échantillonner la frontière 6-connexe). L'entraînement équilibré biaise
les probabilités : `prior_correction: true` réajuste à l'inférence avec les proportions de
tissus des sujets d'entraînement du fold (`src.sampling.adjust_priors`).

Interfaces attendues côté modèles / post-traitement (résolues dynamiquement par la CLI) :
`src.models.registry.build(name, config, seed)` et
`src.postproc.topology.apply_postproc(proba_vol, mask, spacing, steps)`.

## Blocs de features (tous à 0 paramètre appris)

| bloc | fichier | n | contenu |
|---|---|---:|---|
| A intensity | `src/features/intensity.py` | 6 | T1/T2 z-scorés dans le masque, ratio (T1−T2)/(T1+T2) sur intensités normalisées par la médiane, différence des z, rangs percentiles |
| B gaussian | `src/features/gaussian.py` | 68 | σ ∈ {0.5,1,2,4,8} mm × {T1,T2} : lissage, ‖∇‖, laplacien, 3 valeurs propres de la Hessienne triées par \|λ\| (formule analytique vectorisée), différences de gaussiennes ; convolution normalisée par le masque au bord |
| C spatial | `src/features/spatial.py` | 9 | coordonnées normalisées, distance au bord du masque, distance au plan sagittal médian (PCA, orientation fixée), coordonnées sphériques |
| D morpho | `src/features/morpho.py` | 52 | arbre des formes 3D auto-dual (higra) : attributs de la plus petite forme contenant le voxel (aire, profondeur, contraste, dynamique, sphéricité, extension), puis remontée de branche vers les ancêtres de volume ≥ {100, 1000, 10000, 100000} |
| E symmetry | `src/features/symmetry.py` | 4 | intensité au point miroir par rapport au plan sagittal médian, et différence voxel − miroir |
| F context | `src/features/context.py` | 12 | moyenne et écart-type locaux des rangs percentiles (rayons 1, 2, 4 voxels), normalisés par le masque |

Le bloc D apporte le contexte non local qui manque aux blocs A, B et C, tous locaux. L'arbre des
formes est auto-dual, donc T1 et T2 (contrastes inversés) sont traités identiquement par un seul
arbre ; sa structure est invariante par transformation croissante de l'intensité ; et la remontée de
branche lit des descripteurs à toutes les échelles anatomiques sans un seul poids appris.

Ablation du bloc D, leave-one-out sur 10 sujets, régression logistique, 5 000 voxels par tissu et
par sujet, correction des priors (`experiments/logreg_ABC*.yaml`) :

| configuration | features | paramètres | Dice LCR | Dice SG | Dice SB | Dice moyen | Δ |
|---|---:|---:|---:|---:|---:|---:|---:|
| A+B+C, référence | 83 | 418 | 0.846 | 0.804 | 0.763 | 0.8046 | — |
| palier 0, max-tree + min-tree, nœud propre | 107 | 538 | 0.864 | 0.812 | 0.768 | 0.8149 | +0.0103 |
| palier 1, idem + remontée de branche | 187 | 938 | 0.869 | 0.818 | 0.772 | 0.8198 | +0.0152 |
| palier 2, arbre des formes + remontée | 135 | 678 | 0.862 | 0.814 | 0.768 | 0.8149 | +0.0103 |
| palier 3, idem + filtres de grain | 141 | 708 | 0.862 | 0.814 | 0.768 | 0.8148 | +0.0102 |
| palier 3, quantification 64 niveaux | 141 | 708 | 0.861 | 0.813 | 0.768 | 0.8140 | +0.0095 |
| palier 3, quantification linéaire | 141 | 708 | 0.867 | 0.817 | 0.769 | 0.8176 | +0.0130 |

Ce que l'ablation a tranché :
- L'arbre des formes auto-dual atteint 99,4 % du Dice de la paire max-tree/min-tree avec 28 % de
  paramètres en moins. C'est ce qui compte pour un critère Dice / nombre de paramètres.
- Les filtres de grain n'apportent rien : leurs résidus font double emploi avec ceux de la remontée
  de branche. Ils sont désactivés par défaut, l'option reste disponible.
- La quantification linéaire (percentiles 1 et 99) bat la quantification par rang de 0,003. Elle
  préserve les amplitudes de contraste ; le rang les égalise. Elle reste invariante au gain et à
  l'offset d'acquisition, ce qui suffit sur des volumes déjà corrigés en inhomogénéité de champ.

Hyperparamètres fixés a priori (pas appris) : voir `config` de chaque bloc,
recopié dans chaque JSON de résultats sous `feature_config`.

## Structure

```
src/io.py              chargement Analyze 7.5, Subject, masque = T1 != 0 (== label != 0 à 100 %)
src/features/          base.py (interface), cache.py, registry.py, 6 blocs
src/sampling.py        échantillonnage équilibré, sur-échantillonnage de frontière, correction des priors
src/eval/metrics.py    Dice, ASD, MHD (p95 et Dubuisson) par classe et par sujet
src/eval/loocv.py      boucle leave-one-out, JSON partiel après chaque fold, .npz de probabilités
src/cli.py             run / features / blocks
src/models/stub.py     stubs (random, logreg sklearn) en attendant les vrais modèles
experiments/*.yaml     une config par run ; results/*.json un résultat par run
```
