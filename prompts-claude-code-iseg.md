# Hackathon SCIA 2026 — Sujet 2 (iSeg-2017)
## Prompts Claude Code — Jules & Arthur

> **Mode d'emploi.** La section 0 est à coller **dans les deux sessions** Claude Code, en premier.
> Ensuite chacun colle sa propre section (1 pour Jules, 2 pour Arthur) dans sa session.
> Travaillez sur deux branches git séparées (`feat/features` et `feat/models`), merge sur `main` au checkpoint T+12h.

---

# SECTION 0 — CONTRAT COMMUN (à coller dans les deux sessions)

```
# CONTEXTE

Hackathon SCIA 2026, EPITA. Sujet : challenge MICCAI iSeg-2017, segmentation de
cerveaux de nourrissons de 6 mois en 3 tissus depuis des IRM T1 et T2.

CRITÈRE DE NOTATION DU JURY (à garder en tête à chaque décision technique) :
  1. Le Dice RAPPORTÉ AU NOMBRE DE PARAMÈTRES du modèle. Ce n'est PAS "le meilleur
     Dice". C'est un ratio. Un modèle à 3 000 paramètres qui fait 0,86 de Dice bat
     un U-Net à 3 000 000 de paramètres qui fait 0,91.
  2. L'originalité de l'approche.

APPROCHE CHOISIE : pas de deep learning end-to-end. On extrait des descripteurs
NON APPRIS (dérivées de gaussienne, Hessienne, attributs morphologiques, priors
spatiaux) qui coûtent ZÉRO paramètre, puis un classifieur MINUSCULE (régression
logistique ou MLP de quelques milliers de poids) décide du tissu voxel par voxel.
Toute intelligence placée en dehors des poids appris est gratuite au sens du critère.

# LES DONNÉES

- 10 sujets d'entraînement AVEC labels manuels : subject-1 à subject-10.
  Fichiers : subject-N-T1, subject-N-T2, subject-N-label.
- 13 sujets de test SANS labels : subject-11 à subject-23. Inutilisables pour
  mesurer quoi que ce soit. On ne s'en sert QUE pour générer des figures qualitatives.
- Format : Analyze 7.5 (paires .hdr/.img), lisible avec nibabel. VÉRIFIE le format
  réel et la shape avant de coder quoi que ce soit d'autre.
- Valeurs des labels : 0 = fond, 10 = LCR (CSF), 150 = SG (GM), 250 = SB (WM).
  On les remappe en 0/1/2/3 en interne.
- Les volumes sont déjà skull-strippés et corrigés en inhomogénéité de champ.
  Le T2 est déjà recalé rigidement sur le T1 du même sujet.
  Les sujets ne sont PAS recalés entre eux.

CONSÉQUENCE MAJEURE : toute l'évaluation se fait en LEAVE-ONE-OUT sur les 10 sujets
labellisés. 10 folds. Chaque configuration doit donc s'entraîner en quelques minutes
maximum, sinon le budget de 48h explose.

# STRUCTURE DU DÉPÔT

iseg-frugal/
├── data/                      # symlinks vers les données, jamais de copie, jamais commité
├── src/
│   ├── io.py                  # [JULES] chargement volumes + labels + masque
│   ├── features/
│   │   ├── base.py            # [JULES] interface FeatureExtractor
│   │   ├── intensity.py       # [JULES]
│   │   ├── gaussian.py        # [JULES]
│   │   ├── spatial.py         # [JULES]
│   │   ├── morpho.py          # [JULES]
│   │   └── registry.py        # [JULES] composition des blocs
│   ├── sampling.py            # [JULES]
│   ├── models/
│   │   ├── base.py            # [ARTHUR] interface VoxelClassifier
│   │   ├── linear.py          # [ARTHUR]
│   │   ├── mlp.py             # [ARTHUR]
│   │   ├── autocontext.py     # [ARTHUR]
│   │   └── params.py          # [ARTHUR] comptage de paramètres
│   ├── postproc/topology.py   # [ARTHUR]
│   ├── eval/
│   │   ├── metrics.py         # [JULES]
│   │   ├── loocv.py           # [JULES]
│   │   └── pareto.py          # [ARTHUR]
│   └── cli.py                 # [JULES]
├── experiments/               # configs YAML, une par run
├── results/                   # JSON de résultats, un par run, commités
├── figures/
└── report/

# CONTRAT D'INTERFACE — NE JAMAIS LE MODIFIER UNILATÉRALEMENT

Ces signatures sont figées. Si tu as besoin d'un changement, tu le SIGNALES
explicitement dans ta sortie pour que l'autre binôme soit prévenu, tu ne le fais
pas en silence.

## Côté données/features (produit par Jules, consommé par Arthur)

```python
# src/io.py
def load_subject(subject_id: int, root: Path) -> Subject:
    """Subject est une dataclass avec :
       t1: np.ndarray float32, shape (D, H, W)
       t2: np.ndarray float32, même shape
       label: np.ndarray uint8 | None, valeurs 0..3 (0=fond,1=LCR,2=SG,3=SB)
       mask: np.ndarray bool, True = intérieur du cerveau
       subject_id: int
       spacing: tuple[float, float, float]
    """

# src/features/base.py
class FeatureExtractor:
    @property
    def names(self) -> list[str]:
        """Noms des features, dans l'ordre des colonnes. len(names) == n_features."""

    @property
    def n_learned_params(self) -> int:
        """Nombre de paramètres APPRIS de l'extracteur. Doit valoir 0 pour tous
        nos extracteurs. Présent pour l'honnêteté du comptage."""

    def transform(self, subject: Subject) -> np.ndarray:
        """Retourne un tableau float32 de shape (n_voxels_dans_le_masque, n_features).
        L'ordre des voxels est celui de np.flatnonzero(subject.mask), donc
        déterministe et identique d'un appel à l'autre."""

# src/sampling.py
def sample_voxels(subject, n_per_class: int, rng) -> tuple[np.ndarray, np.ndarray]:
    """Retourne (indices_dans_le_masque, labels) échantillonnés de façon
    équilibrée entre les 3 classes de tissu."""
```

## Côté modèles (produit par Arthur, consommé par Jules)

```python
# src/models/base.py
class VoxelClassifier:
    def fit(self, X: np.ndarray, y: np.ndarray) -> "VoxelClassifier":
        """X shape (N, F) float32, y shape (N,) uint8 avec valeurs dans {1,2,3}."""

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        """Retourne (N, 3) float32, probabilités pour LCR/SG/SB, somme à 1."""

    def n_params(self) -> int:
        """Nombre TOTAL de paramètres appris, biais compris."""

    def param_breakdown(self) -> dict[str, int]:
        """Détail par composant, pour le tableau du rapport."""
```

## Format des résultats (results/<run_name>.json)

```json
{
  "run_name": "mlp32_gauss_spatial_autoctx",
  "timestamp": "2026-09-XXTXX:XX:XX",
  "feature_blocks": ["intensity", "gaussian", "spatial"],
  "n_features": 34,
  "model": "MLP",
  "model_config": {"hidden": [32], "activation": "relu"},
  "n_params": 1283,
  "n_params_breakdown": {"layer1": 1120, "layer2": 99, "autocontext_pass2": 64},
  "postproc": ["largest_cc_wm", "fill_holes", "topology_order"],
  "per_subject": {
    "1": {"dice_csf": 0.94, "dice_gm": 0.86, "dice_wm": 0.85,
          "asd_csf": 0.31, "asd_gm": 0.42, "asd_wm": 0.44},
    "...": {}
  },
  "mean": {"dice_csf": 0.0, "dice_gm": 0.0, "dice_wm": 0.0, "dice_mean": 0.0},
  "std":  {"dice_csf": 0.0, "dice_gm": 0.0, "dice_wm": 0.0},
  "train_seconds": 42.0,
  "inference_seconds_per_subject": 8.1
}
```

# RÈGLES DE RIGUEUR — NON NÉGOCIABLES

1. AUCUNE FUITE DE DONNÉES. La normalisation d'intensité se calcule PAR SUJET
   (z-score à l'intérieur du masque cérébral de ce sujet uniquement). Jamais de
   statistique globale calculée sur l'ensemble train+validation. Idem pour toute
   sélection de features ou tout choix d'hyperparamètre : ça se décide à
   l'intérieur du fold, pas en regardant le sujet tenu à l'écart.

2. COMPTAGE DE PARAMÈTRES HONNÊTE. On compte tout poids ajusté sur les données,
   biais inclus. Les sigmas des gaussiennes, les tailles de fenêtres et les seuils
   morphologiques sont fixés a priori et ne comptent pas, MAIS ils sont listés
   explicitement dans le rapport avec leurs valeurs. Un jury qui soupçonne un
   comptage arrangé jette le travail. Le module params.py doit produire un tableau
   vérifiable, pas un chiffre sorti de nulle part.

3. LE FOND N'EST PAS UNE CLASSE. On n'entraîne pas dessus et on ne l'évalue pas.
   Tout se passe dans le masque cérébral. Le Dice se calcule sur 3 classes.

4. DICE PAR SUJET PUIS MOYENNE. Jamais un Dice agrégé sur tous les voxels de tous
   les sujets, ça masque les échecs individuels.

5. SEED FIXÉE ET LOGGÉE partout. Chaque run doit être reproductible à l'identique.

6. Tout tourne sur CPU. Si un modèle a besoin d'un GPU pour s'entraîner, c'est
   qu'il est trop gros pour ce sujet.

7. Pas de dépendance lourde inutile. numpy, scipy, scikit-learn, nibabel,
   matplotlib. torch uniquement pour les MLP si vraiment nécessaire, sinon
   sklearn.neural_network suffit largement à cette échelle. higra pour la morpho.
```

---

# SECTION 1 — PROMPT POUR JULES

```
Tu m'aides sur le hackathon décrit ci-dessus. Je suis Jules, je prends la MOITIÉ
GAUCHE du pipeline : données, features non apprises, échantillonnage, métriques et
boucle de validation croisée. Mon binôme Arthur prend les modèles, le
post-traitement et l'analyse de Pareto. On travaille en parallèle, donc je ne dois
JAMAIS être bloqué par son code et réciproquement.

Travaille en petites étapes, montre-moi le code avant de lancer des choses longues,
et arrête-toi pour me demander quand une décision engage l'architecture.

## T0 — Amorçage (30 min)

1. Inspecte les données dans data/. Trouve le format réel des fichiers, la shape
   des volumes, l'espacement voxel, l'intervalle dynamique de T1 et T2, la
   répartition des labels. Écris un petit script d'inspection et MONTRE-MOI la
   sortie. Ne suppose rien de ce qui est écrit dans le contexte, vérifie.
2. Crée la structure du dépôt, le pyproject/requirements, le .gitignore
   (data/ et results/*.png exclus, results/*.json inclus).
3. Implémente src/io.py conformément au contrat. Le masque cérébral se déduit du
   T1 non nul, mais vérifie sur les données : compare avec (label != 0) sur les
   sujets d'entraînement et dis-moi le taux d'accord. S'il y a un écart, on prend
   la définition la plus sûre et on la documente.
4. Écris un STUB de classifieur dans src/models/stub.py qui respecte l'interface
   VoxelClassifier et prédit au hasard. C'est ma bouchée d'air : il me permet de
   faire tourner toute la chaîne sans attendre Arthur. Il sera supprimé au merge.

## T1 — Métriques et boucle LOO (1h)

5. src/eval/metrics.py : Dice par classe, distance de surface moyenne (ASD) et
   distance de Hausdorff modifiée (MHD), ce sont les métriques officielles du
   challenge. Le Dice est trivial, les distances de surface le sont moins :
   utilise scipy.ndimage.distance_transform_edt sur le complémentaire de chaque
   masque et prends les valeurs sur les voxels de frontière de l'autre. Teste sur
   des cas synthétiques dont je connais la réponse (deux sphères décalées d'un
   voxel, un cube identique à lui-même) avant de faire confiance au code.

6. src/eval/loocv.py : la boucle leave-one-out. Elle prend un FeatureExtractor et
   un VoxelClassifier, tourne 10 folds, écrit le JSON au format du contrat.
   Elle doit logger le temps par fold et être interruptible proprement.
   Elle doit AUSSI sauvegarder les volumes de probabilité prédits en .npy
   compressé pour chaque fold, parce qu'Arthur en aura besoin pour développer son
   post-traitement topologique sans avoir à tout réentraîner.

7. Fais tourner la boucle complète avec le stub aléatoire et des features bidon.
   Objectif : que la plomberie marche de bout en bout avant midi. Le Dice sera
   nul, c'est normal et attendu.

## T2 — Les blocs de features (le gros du travail, 4-5h)

Chaque bloc est un FeatureExtractor indépendant et composable. registry.py permet
de les combiner par leur nom depuis un YAML. Chaque bloc expose ses noms de
features de façon lisible, parce qu'Arthur va faire de la sélection de features
dessus et qu'il aura besoin de savoir ce qu'il garde.

BLOC A — intensity.py
  - T1 et T2 z-scorés DANS LE MASQUE, par sujet.
  - Le ratio normalisé (T1 - T2) / (T1 + T2 + eps). À 6 mois, SG et SB se
    chevauchent en intensité sur chaque modalité prise isolément, mais leur
    comportement RELATIF entre T1 et T2 diffère. Cette feature est probablement la
    plus informative de tout le projet, soigne-la.
  - Rang percentile de chaque voxel dans la distribution intra-masque du sujet.
    C'est une normalisation robuste aux différences de protocole d'acquisition.

BLOC B — gaussian.py
  - Pour sigma dans {0.5, 1, 2, 4, 8} millimètres (attention à convertir en voxels
    via le spacing) et pour chaque modalité :
      lissage gaussien, norme du gradient, laplacien,
      les 3 valeurs propres de la Hessienne TRIÉES par valeur absolue croissante.
  - Le tri des valeurs propres est important : sans tri, les features ne sont pas
    invariantes par rotation et le classifieur apprend du bruit.
  - Différence de gaussiennes entre échelles consécutives.
  - Implémente ça avec scipy.ndimage.gaussian_filter et son argument order, pas à
    la main. Vectorise le calcul des valeurs propres de la Hessienne 3x3 : ne fais
    PAS une boucle np.linalg.eigvalsh sur 7 millions de voxels, utilise la formule
    analytique pour matrices symétriques 3x3 ou au minimum un batch vectorisé.
    Mesure le temps, dis-le-moi, ça doit rester sous la minute par sujet.

BLOC C — spatial.py (le prior anatomique gratuit)
  - Coordonnées x, y, z normalisées par la boîte englobante du masque cérébral.
  - Distance euclidienne au bord du masque, normalisée par le rayon maximal.
    Cette feature à elle seule sépare très bien le LCR périphérique du reste.
  - Distance au plan sagittal médian. Estime ce plan par le centroïde du masque et
    l'axe principal via une PCA sur les coordonnées des voxels du masque. Sois
    prudent : la PCA peut donner un axe retourné, fixe l'orientation par une
    convention explicite.
  - Coordonnées sphériques relatives au centroïde.

BLOC D — morpho.py (le bloc qui fait l'originalité)
  - Utilise higra. Construis l'arbre des formes (tree of shapes) sur le T1 et sur
    le T2, et pour chaque voxel remonte les attributs de la plus petite composante
    qui le contient : aire, profondeur dans l'arbre, contraste avec le parent,
    compacité, extension de la boîte englobante.
  - Ajoute des ouvertures et fermetures par attribut d'aire à quelques seuils,
    ainsi que les résidus (image moins son ouverture).
  - C'est le bloc le plus risqué en temps d'implémentation. Time-boxe-le à 2h.
    Si higra pose problème sur du 3D, replie-toi sur des ouvertures/fermetures
    morphologiques classiques avec des éléments structurants sphériques de
    plusieurs rayons, plus les gradients morphologiques associés. C'est moins
    élégant mais ça marche et ça reste à zéro paramètre.
  - Documente précisément ce que tu fais, ce bloc sera le cœur de la section
    "originalité" du rapport.

Après chaque bloc : relance la boucle LOO avec une simple régression logistique de
sklearn et note le Dice. Je veux voir la progression bloc par bloc, c'est ce qui
fera le tableau d'ablation du rapport.

## T3 — Échantillonnage (1h)

8. src/sampling.py. Échantillonnage équilibré entre les 3 tissus, avec une option
   de suréchantillonnage des voxels de frontière (voxels dont le voisinage 6-connexe
   contient au moins deux classes). La frontière SG/SB est là où tout se joue,
   c'est là qu'il faut mettre les exemples.
   ATTENTION, point subtil à implémenter et à documenter : si on entraîne sur une
   distribution rééquilibrée, les probabilités prédites sont biaisées par rapport à
   la vraie distribution des tissus. Il faut corriger à l'inférence en ajoutant
   log(prior_reel / prior_echantillonnage) aux logits. Signale ce point à Arthur,
   c'est à la frontière de nos deux périmètres, et vérifie empiriquement que la
   correction améliore bien le Dice.

## T4 — CLI et reproductibilité

9. src/cli.py : `python -m src.cli run experiments/foo.yaml` doit suffire à
   reproduire n'importe quel résultat. Le YAML décrit les blocs de features, le
   modèle, le post-traitement, la seed.
10. Un Makefile avec des cibles courtes pour les runs qu'on relancera souvent.

## CE QUE JE NE VEUX PAS

- Pas de U-Net, pas de torch pour l'instant, pas de GPU.
- Pas de features qui coûtent des paramètres appris sans que ce soit signalé.
- Pas de calcul de features à la volée pendant l'entraînement : on précalcule et on
  met en cache sur disque (npy memmap) une fois par sujet, sinon on va passer le
  hackathon à recalculer des gaussiennes.
- Pas de fonctions de 200 lignes. Chaque bloc de features est testable isolément.

## LIVRABLES DE MA MOITIÉ

- Un pipeline qui va du .hdr au JSON de résultats en une commande.
- 4 blocs de features composables, tous à 0 paramètre appris.
- Un cache disque des features par sujet.
- Un tableau d'ablation bloc par bloc, avec Dice moyen et écart-type en LOO.
```

---

# SECTION 2 — PROMPT POUR ARTHUR

```
Tu m'aides sur le hackathon décrit ci-dessus. Je suis Arthur, je prends la MOITIÉ
DROITE du pipeline : classifieurs minuscules, comptage de paramètres,
post-traitement topologique, sélection de features et analyse de Pareto. Mon binôme
Jules fait le chargement des données, les features non apprises et la boucle de
validation croisée. On travaille en parallèle, donc je ne dois JAMAIS être bloqué
par son code et réciproquement.

Travaille en petites étapes, montre-moi le code avant de lancer des choses longues,
et arrête-toi pour me demander quand une décision engage l'architecture.

## T0 — Amorçage sans dépendre de Jules (30 min)

1. Écris src/fake_data.py : un générateur de données synthétiques qui imite la
   sortie de Jules. Il produit un volume 3D jouet (par exemple trois coquilles
   concentriques bruitées représentant LCR, SG, SB), un masque, un label, et une
   matrice de features (N, F) plausible. Tout mon développement se fait dessus
   jusqu'au merge. C'est ce qui me rend indépendant.
2. Crée src/models/base.py avec l'interface VoxelClassifier du contrat, et
   src/models/params.py.

## T1 — Le comptage de paramètres (1h, c'est le cœur du sujet)

3. params.py doit produire, pour n'importe quel modèle, un décompte vérifiable :
   - Pour un modèle linéaire : (n_features + 1) * (n_classes - 1) si on
     paramétrise proprement, ou (n_features + 1) * n_classes si on utilise la
     forme redondante de sklearn. Choisis une convention, JUSTIFIE-LA en
     commentaire, et applique-la partout.
   - Pour un MLP : somme des poids et biais de chaque couche.
   - Pour un modèle à base d'arbres : nombre de nœuds de décision fois 2 (seuil +
     indice de feature) plus les valeurs de feuilles. C'est une convention, il faut
     l'écrire noir sur blanc.
   - Une fonction qui compare le décompte manuel au décompte automatique
     (par exemple sum(p.numel() for p in model.parameters()) côté torch, ou la
     somme des tailles de coefs_ et intercepts_ côté sklearn) et LÈVE UNE ERREUR
     en cas de désaccord. Je ne veux pas d'un chiffre auquel on ne peut pas se fier.
4. Écris des tests unitaires sur ce module. C'est le seul endroit du projet où je
   veux des tests systématiques, parce que c'est le dénominateur de notre note.

## T2 — La famille de modèles (3h)

Tous respectent VoxelClassifier. Objectif : couvrir 3 ordres de grandeur en nombre
de paramètres, de ~50 à ~50 000, pour que la courbe de Pareto ait des points partout.

M0 — Régression logistique sur T1 et T2 bruts uniquement. Environ 9 paramètres.
     C'est notre plancher et notre point de référence "à quel point les features
     de Jules apportent-elles quelque chose".
M1 — Régression logistique sur toutes les features. Quelques centaines de paramètres.
M2 — MLP à une couche cachée, largeur balayée sur {4, 8, 16, 32, 64}. Utilise
     sklearn.neural_network.MLPClassifier d'abord pour aller vite ; ne passe à
     torch que si j'ai besoin de quelque chose que sklearn ne sait pas faire.
M3 — MLP à deux couches cachées, quelques configurations seulement.
M4 — Un arbre de gradient boosting très peu profond (profondeur 3, peu d'arbres),
     comme point non neuronal de la courbe. Compte les paramètres selon la
     convention établie en T1.

M5 — AUTO-CONTEXTE. C'est l'idée la plus importante de ma moitié, priorise-la dès
     que M2 marche. Le problème de notre approche est que les descripteurs sont
     LOCAUX : le classifieur ne voit pas le contexte anatomique large, alors que la
     frontière SG/SB à 6 mois se devine surtout par le contexte. Solution : on
     entraîne un premier classifieur, on prédit les 3 cartes de probabilité sur
     tout le volume, on LISSE ces cartes à plusieurs échelles gaussiennes (sigma
     2, 4, 8) et on les réinjecte comme features supplémentaires dans un second
     classifieur. Deux passes suffisent généralement. Le coût est de 3 * 4 = 12
     features en plus, donc quelques centaines de paramètres, pour un champ
     réceptif effectif énorme. C'est la technique de Tu & Bai, elle est ancienne,
     elle marche très bien, et elle colle parfaitement à notre contrainte de
     frugalité.
     Point de vigilance : la deuxième passe doit être entraînée sur des cartes de
     probabilité produites en VALIDATION CROISÉE INTERNE au fold, pas sur des
     cartes produites par un modèle qui a vu ces voxels en entraînement. Sinon la
     deuxième passe apprend à faire confiance à des probabilités anormalement
     bonnes et s'effondre au test. Fais une CV interne à 3 plis sur les 9 sujets
     d'entraînement du fold. C'est le piège classique de l'auto-contexte, ne le
     rate pas.

## T3 — Post-traitement topologique (2h)

C'est du gain de Dice à ZÉRO paramètre, donc c'est du gain pur sur notre critère.
Implémente dans src/postproc/topology.py, chaque opération activable indépendamment
pour pouvoir mesurer sa contribution :

5. Champ aléatoire de Markov / régularisation spatiale : lissage des cartes de
   probabilité avant l'argmax, ou une passe d'ICM (iterated conditional modes) avec
   un potentiel de Potts. Le poids du potentiel est un hyperparamètre fixé, pas
   appris — donc gratuit, mais à déclarer.
6. Plus grande composante connexe pour la substance blanche. La SB est un objet
   connexe (aux deux hémisphères près, donc garde les 2 plus grandes composantes et
   vérifie que c'est bien le bon choix sur les labels de référence).
7. Bouchage des trous : les trous de SB à l'intérieur de la SB sont des erreurs,
   les trous de LCR à l'intérieur de la SB sont les ventricules et sont RÉELS.
   Attention à ne pas les détruire, vérifie visuellement.
8. Contrainte d'ordre des tissus : en allant de l'extérieur vers l'intérieur on
   traverse LCR, puis SG, puis SB. Un voxel de SB directement adjacent à du LCR
   sans SG entre les deux est presque toujours une erreur. Implémente une
   correction de ces violations et mesure combien il y en a avant/après.
9. Ouverture/fermeture morphologique par attribut d'aire pour supprimer les îlots
   de moins de N voxels.

Pour développer tout ça sans attendre : Jules sauvegarde les volumes de probabilité
prédits de chaque fold en .npy. Charge-les et travaille dessus directement, tu n'as
pas besoin de réentraîner.

## T4 — Sélection de features (2h)

Le nombre de paramètres d'un modèle linéaire ou d'un MLP est PROPORTIONNEL au
nombre de features d'entrée. Réduire les features réduit donc directement le
dénominateur de notre score. C'est un levier majeur et il est entièrement dans mon
périmètre.

10. Sélection avant gloutonne : pars de zéro feature, ajoute à chaque étape celle
    qui améliore le plus le Dice en validation interne, arrête-toi quand le gain
    passe sous un seuil. Trace la courbe Dice vs nombre de features retenues.
11. Compare avec une régression logistique L1 et avec un classement par importance
    de permutation.
12. RÈGLE ABSOLUE : la sélection se fait à l'intérieur de chaque fold, sur les 9
    sujets d'entraînement. Si tu sélectionnes les features en regardant les 10
    sujets, tout notre protocole est invalide et le jury le verra.
13. Livrable attendu : "avec seulement 12 features sur 60, on garde 98 % du Dice et
    on divise les paramètres par 5". C'est exactement le genre de phrase qui gagne
    ce hackathon.

## T5 — Pareto et figures (2h)

14. src/eval/pareto.py : agrège tous les JSON de results/, trace le nuage
    (nombre de paramètres en log, Dice moyen), identifie le front de Pareto,
    annote chaque point avec sa configuration.
15. Ajoute sur la même figure, en points de référence, les scores publiés des
    équipes du challenge iSeg-2017 avec leur ordre de grandeur de paramètres.
    Les chiffres sont dans le papier de benchmark (IEEE TMI 2019). Si tu ne trouves
    pas les comptes de paramètres exacts, mets des estimations et DIS
    EXPLICITEMENT sur la figure que ce sont des estimations. Ne fabrique jamais un
    chiffre en le présentant comme exact.
16. Figures qualitatives : coupes axiales avec vérité terrain, prédiction, et carte
    d'erreur, pour le meilleur et le pire sujet en LOO. Plus quelques coupes sur des
    sujets de test non labellisés.
17. Un tableau récapitulatif en markdown, généré automatiquement depuis les JSON,
    directement collable dans le rapport.

## CE QUE JE NE VEUX PAS

- Pas de modèle dont je ne peux pas justifier le compte de paramètres à la ligne près.
- Pas de sélection de features ou d'hyperparamètre choisi en regardant le sujet
  tenu à l'écart.
- Pas de post-traitement qui introduit des paramètres appris sans que ce soit compté.
- Pas de course au Dice absolu : si un modèle gagne 0,5 point de Dice en multipliant
  les paramètres par 10, il est MOINS BON pour nous. Dis-le-moi quand ça arrive.

## LIVRABLES DE MA MOITIÉ

- Une famille de modèles couvrant 3 ordres de grandeur en paramètres.
- Un module de comptage de paramètres testé et fiable.
- L'auto-contexte fonctionnel, avec sa CV interne correcte.
- Un post-traitement topologique dont chaque brique a sa contribution mesurée.
- La courbe de Pareto et le tableau récapitulatif du rapport.
```

---

# Points de synchronisation

| Moment | Ce qui doit être vrai |
|---|---|
| T+2h | Jules : io.py + stub tournent. Arthur : fake_data.py + params.py tournent. |
| T+6h | Jules : blocs A, B, C faits. Arthur : M0, M1, M2 faits. **Merge sur main.** |
| T+12h | Premier vrai chiffre en LOO avec vraies features et vrai modèle. **Merge.** |
| T+20h | Auto-contexte et post-traitement branchés. Bloc morpho fait ou abandonné. |
| T+30h | Sélection de features finie, grille de runs lancée pour le Pareto. Gel du code. |
| T+36h | Uniquement figures et rapport. Plus aucune nouvelle idée technique. |
| Samedi 23h59 | Rapport envoyé à Nicolas.Boutry@epita.fr. |

Le gel du code à T+30h est la règle la plus importante de ce tableau. Un beau
résultat non rédigé vaut zéro.
