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
| D morpho | `src/features/morpho.py` | 42 | arbre des formes 3D (higra) : aire, profondeur, contraste, hauteur, compacité, extension ; profil d'attributs des ancêtres de volume ≥ {100, 1000, 10000} ; top-hats par ouverture/fermeture d'aire {50, 500, 5000} |
| E symmetry | `src/features/symmetry.py` | 4 | intensité au point miroir par rapport au plan sagittal médian, et différence voxel − miroir |
| F context | `src/features/context.py` | 12 | moyenne et écart-type locaux des rangs percentiles (rayons 1, 2, 4 voxels), normalisés par le masque |

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
