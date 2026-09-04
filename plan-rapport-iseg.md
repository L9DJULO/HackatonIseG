# Plan du rapport — Hackathon SCIA 2026, sujet 2 (iSeg-2017)

**Hypothèses de travail :** rapport technique en français, une dizaine de pages, rendu unique
pour le binôme. Si Boutry a imposé un format, une longueur ou l'anglais, tout le plan
se comprime proportionnellement — la hiérarchie des sections reste valable.

---

## La thèse du rapport

Tout le document défend une seule affirmation, et chaque section doit y contribuer :

> Sur la segmentation de cerveaux de nourrissons en phase isointense, on atteint une
> fraction substantielle du Dice des méthodes publiées avec trois à quatre ordres de
> grandeur moins de paramètres, en déplaçant l'information des poids appris vers des
> descripteurs géométriques et hiérarchiques calculés à la volée.

Si une section ne sert pas cette thèse, elle sort.

---

## Structure

### 1. Introduction (¾ page)

- Le problème clinique : segmentation en trois tissus, base de toute étude de
  développement cérébral, plusieurs heures par cerveau à la main.
- **La phase isointense.** C'est la justification de tout le reste : à 6 mois la
  myélinisation est à mi-course, substance grise et blanche ont presque la même
  intensité. Aucune méthode fondée sur la valeur d'un point ne peut fonctionner.
  Cette phrase doit apparaître dès l'introduction, appuyée par la figure 1.
- Le critère du hackathon, et la thèse ci-dessus énoncée explicitement.
- Annonce du plan en trois lignes.

### 2. Position du problème et métrique (¾ page)

- Les données : 10 sujets labellisés, 13 sans labels. Conséquence directe et
  assumée : toute l'évaluation est en leave-one-out sur 10, il n'y a pas de test
  externe possible. Dire cette limite ici, tôt, plutôt que de la laisser découvrir.
- **Pourquoi le ratio brut Dice/paramètres n'est pas une métrique de sélection.**
  Section courte mais indispensable, et c'est un point de maturité. Le Dice croît
  logarithmiquement avec les paramètres, donc un ratio brut est toujours maximisé
  par le modèle le plus petit ; poussé à la limite il désigne le classifieur qui
  prédit la classe majoritaire. Donnez le calcul sur vos propres configurations
  pour montrer que vous l'avez vérifié, pas seulement supposé.
- Ce qu'on utilise à la place : le front de Pareto, et la comparaison d'ordre de
  grandeur avec les méthodes publiées.

### 3. Méthode (3 pages, le cœur)

**3.1 Principe.** Classification voxel par voxel. Chaque voxel devient une ligne
décrite par des colonnes calculées à la volée ; un classifieur minuscule lit la
ligne. Le principe directeur en une phrase : tout ce qui se recalcule sur le sujet
courant est gratuit, tout ce qui se mémorise du jeu d'entraînement coûte. Figure 2
(le pipeline) ici.

**3.2 Les six blocs de descripteurs.** Un paragraphe court chacun, en disant à
chaque fois *quelle information manquante il apporte*, pas seulement ce qu'il
calcule.
- A, intensités : et surtout le ratio T1/T2, puisque les distributions se
  chevauchent modalité par modalité mais que le comportement croisé sépare.
- B, gaussiennes : texture et géométrie locale, dérivées et valeurs propres de la
  hessienne triées, invariance par rotation.
- C, spatial : a priori anatomique gratuit, distance à la surface, position.
- D, morphologie : voir 3.3.
- E, symétrie : intensité au point miroir controlatéral et écart au miroir.
- F, contexte : statistiques locales des rangs percentiles à trois rayons.

**3.3 Arbre des formes et remontée de branche.** C'est la section d'originalité, et
elle mérite une page entière avec la figure 3.
- Le constat qui la motive : les blocs A à C sont tous locaux, or la frontière
  substance grise / blanche ne se voit pas localement à cet âge.
- La construction : composantes des seuillages haut et bas, saturation des trous,
  emboîtement par inclusion, arbre unique auto-dual.
- Les propriétés, en étant précis sur ce que vous conservez : l'auto-dualité, oui.
  L'invariance au contraste, **non** — vous l'avez perdue en adoptant la
  quantification linéaire. Dites-le. Un jury du LRDE le verra, et l'assumer vaut
  infiniment mieux que le revendiquer à tort.
- La remontée de branche, qui est votre vraie contribution : les attributs des
  ancêtres à quatre échelles d'aire donnent du contexte multi-échelle à zéro
  paramètre. Expliquez la récurrence en une passe sur les nœuds.

**3.4 Classifieur et post-traitement.** La moitié d'Arthur. Modèles, auto-contexte
avec sa validation croisée interne, contraintes topologiques, sélection de features.

**3.5 Convention de comptage des paramètres.** Mettez ça dans un encadré, pas noyé
dans le texte. Ce qui compte, ce qui ne compte pas, et pourquoi. Le point clé :
la standardisation est intra-sujet, recalculée sur le sujet segmenté, donc elle ne
transporte rien du jeu d'entraînement. **Donnez aussi le chiffre selon la convention
inverse** (avec le scaler compté), en une phrase. Un jury en désaccord avec votre
convention doit trouver son propre chiffre dans votre texte plutôt que de vous
soupçonner de l'avoir caché. C'est le paragraphe qui établit votre crédibilité sur
tout le reste.

### 4. Protocole expérimental (1 page)

- Leave-one-out à 10 plis, seeds fixées, une commande de reproduction.
- **Le contrôle anti-fuite.** Décrivez le test mécanique : les features doivent être
  identiques bit à bit avec le vrai label, avec un label permuté, et sans label.
  C'est plus fort qu'une relecture de code et ça se dit en deux phrases. Peu
  d'équipes auront ça, mettez-le en valeur.
- Métriques : Dice, plus ASD et MHD puisque ce sont les métriques officielles du
  challenge.
- **Protocole statistique.** Comparaisons appariées sur les mêmes 10 sujets, test de
  Wilcoxon signé, taille d'effet de Cohen, nombre de sujets améliorés sur 10, et
  correction de Holm pour la multiplicité. Justifiez le nombre de sujets améliorés
  comme critère : avec n = 10, l'amplitude est bruitée mais la systématicité ne
  l'est pas.

### 5. Résultats (2 pages ½)

- **Tableau d'ablation** : configuration, features, paramètres, Dice par tissu,
  Dice moyen, écart-type, Δ, sujets améliorés, p brut et p ajusté.
- **Figure 4, le front de Pareto** en abscisse logarithmique, avec vos
  configurations et les entrées publiées du challenge en points de référence. Si les
  comptes de paramètres des méthodes publiées ne sont pas disponibles, mettez des
  estimations et écrivez sur la figure que ce sont des estimations. Ne fabriquez
  jamais un chiffre en le présentant comme exact.
- **Budget de frugalité** : paramètres, extraction par sujet décomposée par bloc,
  entraînement, inférence, pic mémoire, taille du modèle sur disque. L'argument :
  la frugalité n'est pas seulement paramétrique, elle est mesurée de bout en bout,
  et le modèle entier tient dans quelques kilo-octets.
- Le résultat sur la quantification à 64 niveaux : présentez-le comme un levier de
  frugalité mesuré, pas comme une note de bas de page.
- **Figure 6, qualitatif** : meilleur et pire sujet, vérité terrain, prédiction,
  carte d'erreur. Commentez le pire cas, ne le cachez pas.

### 6. Discussion (1 page ½)

C'est la section qui distingue un bon rapport d'un compte rendu d'expériences.

- Ce qui apporte le plus, et l'interprétation : le contexte non local paye, la
  description locale plafonne. Reliez-le à la phase isointense de l'introduction.
- **Le résultat négatif sur l'auto-dualité.** Assumez-le pleinement et donnez-lui
  de la place. L'arbre des formes divise bien par deux le nombre de colonnes à
  attributs identiques, comme la théorie le prédit, mais ne produit pas de gain de
  Dice distinguable face à la paire max-tree/min-tree. Vos hypothèses sur le
  pourquoi. Un résultat négatif proprement établi vaut mieux qu'un argument
  fragile, et il montre que vous savez lire vos propres chiffres contre vos propres
  attentes.
- Le choix non départagé sur la quantification, présenté comme tel.
- **Limites**, sans complaisance : 10 sujets, pas de test externe, pas de soumission
  au serveur du challenge, donc vos chiffres ne sont pas directement comparables
  aux scores publiés et vous devez l'écrire. Le plafond de l'approche locale.
- Pistes : arbre des formes multivarié sur T1 et T2 conjointement, plus d'échelles
  d'ancêtres, contraintes topologiques plus fortes.

### 7. Conclusion (¼ page)

Reprise de la thèse avec les chiffres finaux. Rien de neuf.

---

## Les six figures

| # | Contenu | Priorité | Chez qui |
|---|---|---|---|
| 1 | Coupe T1, T2 et labels montrant l'isointensité SG/SB | **critique** — elle justifie tout le rapport | Jules |
| 2 | Schéma du pipeline, avec les blocs à 0 paramètre distingués | haute | Jules |
| 3 | Arbre des formes : emboîtement et remontée de branche | haute — c'est l'originalité | Jules |
| 4 | Front de Pareto, abscisse log, méthodes publiées en référence | **critique** — c'est l'argument central | Arthur |
| 5 | Ablation en barres avec intervalles de confiance | moyenne | Arthur |
| 6 | Qualitatif meilleur/pire sujet + carte d'erreur | haute | Arthur |

La figure 1 est la plus sous-estimée. Elle prouve visuellement que le problème est
dur, et sans elle toute votre approche a l'air d'une complication gratuite.

---

## Ce qui s'écrit maintenant, avant qu'Arthur ait fini

Environ 60 % du rapport ne dépend d'aucun chiffre final : sections 1, 2, 3.1 à 3.3,
3.5 et 4, plus les figures 1, 2 et 3. Attaque ça immédiatement pendant qu'Arthur
termine l'auto-contexte et le post-traitement topologique.

Laisse des marqueurs explicites du type `[[CHIFFRE:dice_final]]` partout où un
nombre manque, et remplace-les à la toute fin depuis `facts.md`. Ne jamais recopier
un chiffre de mémoire ni d'un ancien message : trois valeurs de Dice différentes ont
déjà circulé dans ce projet, et une seule contradiction numérique dans un rapport
rend tout le reste suspect.

---

## Les quatre arguments qui doivent atterrir

Si le jury ne retient que quatre choses, ce sont celles-ci. Chacune doit être
défendable en une phrase à l'oral.

1. **Le déplacement de l'information.** Tout ce qui se recalcule est gratuit ; le
   modèle ne mémorise que quelques centaines de nombres.
2. **La rigueur du comptage.** La convention est explicite, et le chiffre selon la
   convention inverse est donné.
3. **La rigueur statistique.** Aucune amélioration n'est affirmée sans test apparié,
   taille d'effet et nombre de sujets améliorés.
4. **L'honnêteté.** Un résultat négatif documenté, une invariance revendiquée puis
   retirée, un choix laissé non départagé.

Les points 2, 3 et 4 ne coûtent presque rien à produire et sont exactement ce qui
manque à la plupart des rendus de hackathon.
