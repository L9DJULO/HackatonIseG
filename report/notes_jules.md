# Notes de la moitié "données / features / éval" (Jules)

## Faits vérifiés sur les données (scripts/inspect_data.py)
- Analyze 7.5 (nibabel `Spm2AnalyzeImage`), shape (144,192,256,1) squeezée en (144,192,256), int16 0..1000,
  spacing 1 mm isotrope, affine diag(-1,1,1) => axes image = (G-D, A-P, S-I). Sujet test 23 : (160,192,256).
- Labels {0,10,150,250} remappés en {0,1,2,3}. Proportions intra-masque moyennes ≈ CSF 22 % / GM 47 % / WM 31 %.
- Masque cérébral = (T1 != 0). IoU avec (label != 0) = 1.000 sur les 10 sujets. T2 a parfois 1 voxel nul en moins.
- À 6 mois, GM et WM sont quasi isointenses : sur le sujet 1, T1 moyen GM 235 / WM 257, T2 303 / 297.

## Décisions et pièges rencontrés
1. **Ratio (T1−T2)/(T1+T2)** : sur intensités brutes, il est décalé de +0.4 sur le sujet 7 (gain différent) et
   la logreg y obtient Dice GM = 0.000. Corrigé en normalisant chaque modalité par sa médiane intra-masque.
2. **Bloc gaussien** : calcul sur la boîte englobante + 4σmax, zéro hors masque, dérivées normalisées en
   échelle (σ pour l'ordre 1, σ² pour l'ordre 2). 68 features en ~33 s/sujet. Valeurs propres 3×3 analytiques
   (Smith 1961), testées contre `np.linalg.eigvalsh` et sur l'invariance par rotation.
3. **Plan sagittal médian** : PCA sur les coordonnées du masque, l'axe le plus aligné avec l'axe image 0 est
   pris comme normale, signe forcé positif. Sur le sujet 1 les axes PCA ≈ identité (tilt 5°).
4. **Arbre des formes 3D** (higra, immersion Khalimsky) : 12 s et 1 Go sur la boîte englobante (2 M voxels),
   pas besoin du repli sur la morpho classique. Image quantifiée par rang (256 niveaux) => invariante au gain.
   Le contraste ancêtre/parent est constant (1 niveau) dans un arbre aussi imbriqué : remplacé par la hauteur.
5. **MHD** : deux définitions circulent (p95 des distances de surface vs Dubuisson-Jain). Les deux sont
   implémentées, `mhd_*` dans les JSON = p95. À confirmer avec le papier iSeg (TMI 2019) avant le rapport.
6. **Échantillonnage** : `boundary_frac` = fraction MINIMALE de chaque classe tirée sur la frontière 6-connexe,
   le reste uniformément sur toute la classe.

## Messages pour Arthur (interfaces que la CLI attend de sa moitié)
- `src/models/registry.py` avec `build(name: str, config: dict, seed: int) -> VoxelClassifier`. Si absent, la
  CLI retombe sur `src/models/stub.py` (random, logreg). Le stub compte `(n_features+1)*3 + 2*n_features`
  (forme redondante sklearn + scaler) : convention à trancher dans `params.py`.
- `src/postproc/topology.py` avec `apply_postproc(proba_vol (D,H,W,3) float32, mask bool, spacing, steps: list[str]) -> label uint8 (0..3)`.
  Appelé seulement si le YAML a `postproc: [...]` non vide.
- Probabilités de chaque fold : `results/proba/<run>/subject-k.npz` (`proba` float16 (n_mask,3), `mask`).
  Reconstruire le volume avec `src.io.mask_to_volume(proba, mask)`.
- **Correction des priors** : entraînement équilibré (1/3 par classe) => à l'inférence `p_c ∝ p_c · π_c / (1/3)`
  avec π estimé sur les 9 sujets d'entraînement du fold (`src.sampling.adjust_priors`). Activable par
  `sampling.prior_correction: true`. À porter dans l'auto-contexte : la 2e passe doit voir des probabilités
  corrigées de la même manière qu'au test.
- Les noms de features sont dans chaque JSON (`feature_names`, préfixés par le bloc) pour la sélection.
