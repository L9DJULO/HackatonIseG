---
title: "Segmentation frugale des IRM cérébrales de nourrissons en phase isointense"
subtitle: "Hackathon SCIA 2026 — sujet 2, challenge MICCAI iSeg-2017"
author:
  - Jules Lange
  - "Arthur [[NOM:arthur]]"
date: "septembre 2026"
abstract: |
  [[RÉSUMÉ : à rédiger en dernier, une fois les chiffres finaux disponibles.]]
lang: fr
documentclass: article
papersize: a4
fontsize: 11pt
geometry:
  - margin=2.4cm
mainfont: "Latin Modern Roman"
sansfont: "Latin Modern Sans"
monofont: "Latin Modern Mono"
numbersections: true
secnumdepth: 3
colorlinks: true
linkcolor: black
citecolor: black
urlcolor: black
link-citations: true
reference-section-title: "Références"
---

# Introduction

La segmentation d'une IRM cérébrale en liquide céphalo-rachidien, substance grise et
substance blanche est le point de départ de presque toute étude du développement du
cerveau. Épaisseur corticale, volumes tissulaires, courbes de croissance, cartes de
myélinisation : toutes ces mesures se calculent sur une carte de tissus, et aucune ne vaut
mieux que la segmentation dont elle part. Tracée à la main par un expert, une telle carte
demande plusieurs heures par cerveau. Le challenge MICCAI iSeg-2017 [@wang2019iseg]
fournit pour ce problème des volumes T1 et T2 de nourrissons de six mois, avec dix sujets
annotés.

Six mois est précisément l'âge où le problème devient difficile. La myélinisation est à
mi-course, et la substance grise et la substance blanche ont presque la même intensité :
c'est la phase isointense. La \figref{fig:isointense} la montre et la chiffre. Sur les dix
sujets annotés, les distributions d'intensité des deux tissus se recouvrent à
$0{,}701 \pm 0{,}048$ en T1 et à $0{,}867 \pm 0{,}041$ en T2, au sens du coefficient de
recouvrement défini en \figref{fig:isointense}. L'estimateur est légèrement pessimiste, et
nous l'avons mesuré : sur deux moitiés tirées au hasard des seuls voxels de substance
grise, dont le recouvrement vrai vaut 1, il rend $0{,}991$. L'écart est donc réel. La
conséquence est directe. Sur un problème à deux classes d'effectifs égaux, la meilleure
règle de décision concevable fondée sur la seule intensité d'un voxel se trompe sur la
moitié de l'aire de recouvrement : son exactitude plafonne à 65,0 % en T1 et à 56,6 % en
T2. Même en lisant les deux modalités conjointement, le plafond monte seulement à 69,3 %.
Aucune méthode fondée sur la valeur d'un point ne peut fonctionner ici. L'information
doit venir d'ailleurs : de la géométrie locale, de la position anatomique, et de la façon
dont les régions s'emboîtent les unes dans les autres.

\begin{figure}[t]
\centering
\includegraphics[width=\linewidth]{report/assets/fig01_isointense.pdf}
\caption{La phase isointense, sur le sujet 3 et une coupe axiale au niveau des ventricules
latéraux. (a)~T1, (b)~T2, (c)~segmentation manuelle de référence, (d)~histogrammes des
intensités de la substance grise et de la substance blanche, pour les deux modalités, sur
l'ensemble du volume. L'aire sombre est le recouvrement, mesuré par
$\mathrm{OVL} = \sum_b \min\!\big(p_{\mathrm{SG}}(b), p_{\mathrm{SB}}(b)\big)$ où
$p_{\mathrm{SG}}$ et $p_{\mathrm{SB}}$ sont les histogrammes normalisés des deux tissus sur
256~classes réparties linéairement sur l'étendue des intensités intra-masque. Il vaut 0
pour deux distributions disjointes et 1 pour deux distributions identiques. Le sujet est
celui dont les quatre recouvrements mesurés sont les plus proches de la moyenne des dix
($|z| \le 0{,}32$), et la coupe est celle qui maximise l'interface entre les deux tissus.}
\label{fig:isointense}
\end{figure}

Le critère du hackathon met le Dice obtenu en regard du nombre de paramètres appris. Ce
rapport défend une seule affirmation, et chaque section y contribue : sur la segmentation
de cerveaux de nourrissons en phase isointense, on atteint une fraction substantielle du
Dice des méthodes publiées avec trois à quatre ordres de grandeur moins de paramètres, en
déplaçant l'information des poids appris vers des descripteurs géométriques et
hiérarchiques calculés à la volée. Notre configuration finale obtient un Dice moyen de
[[CHIFFRE:dice_final]] pour [[CHIFFRE:parametres_final]] paramètres appris.

La suite est organisée ainsi. La \secref{sec:probleme} pose les données, la limite
d'évaluation qu'elles imposent, et explique pourquoi le ratio brut du Dice sur le nombre de
paramètres ne peut pas servir de critère de sélection. La \secref{sec:methode} décrit la
méthode : le principe de déplacement de l'information, les six blocs de descripteurs,
l'arbre des formes et la remontée de branche, le classifieur, et la convention de comptage
des paramètres. Les sections suivantes donnent le protocole, les résultats et la
discussion.

# Position du problème et métrique {#sec:probleme}

Le jeu iSeg-2017 comprend dix sujets annotés et treize sujets sans annotation publique.
Chaque sujet fournit un volume T1 et un volume T2 de $144 \times 192 \times 256$ voxels de
1 mm isotrope, et, pour les dix premiers, une carte de référence à trois tissus tracée
manuellement. La conséquence est immédiate et nous l'assumons : toute notre évaluation est
un leave-one-out sur dix sujets, et il n'existe pas de jeu de test externe. Les treize
sujets restants ne servent qu'à des figures qualitatives, faute de vérité terrain. Nos
chiffres ne sont donc pas directement comparables aux scores publiés du challenge, qui sont
calculés par le serveur d'évaluation sur ces treize sujets. Nous préférons le dire ici
plutôt que de le laisser découvrir.

Le critère du hackathon invite à rapporter le Dice au nombre de paramètres. Ce rapport ne
doit jamais être maximisé tel quel. Le Dice croît lentement, à peu près
logarithmiquement, avec le nombre de paramètres, tandis que le dénominateur croît
linéairement : le quotient est donc systématiquement maximisé par le plus petit modèle de
la liste, quelle que soit sa qualité. Poussé à sa limite, il désigne le classifieur qui
prédit partout la classe majoritaire.

Nous avons fait le calcul sur nos propres configurations plutôt que de le supposer. Le
\tabref{tab:ratio} le donne. Notre configuration de référence, celle qui n'a aucun
descripteur morphologique et le plus mauvais Dice de toutes les configurations réelles,
obtient le meilleur ratio brut de toutes. Notre configuration finale, qui a le meilleur
Dice, arrive huitième sur neuf. Et le classifieur dégénéré, qui mémorise un seul nombre,
l'indice du tissu majoritaire des neuf sujets d'entraînement, obtient un Dice moyen de
$0{,}214 \pm 0{,}008$ et un ratio brut soixante-sept fois supérieur à celui de la meilleure
configuration réelle. Une métrique qui classe ce modèle premier n'est pas une métrique de
sélection.

| configuration | paramètres | Dice moyen | Dice / paramètres |
|:------------------------------------------------|-----------:|-----------:|------------------:|
| classifieur dégénéré : tissu majoritaire partout | 1          | 0,2139     | $2{,}14 \cdot 10^{-1}$ |
| A+B+C, sans morphologie (référence)              | 252        | 0,8055     | $3{,}20 \cdot 10^{-3}$ |
| palier 0 : max-tree + min-tree, nœud propre      | 324        | 0,8156     | $2{,}52 \cdot 10^{-3}$ |
| palier 2 : arbre des formes + remontée           | 408        | 0,8154     | $2{,}00 \cdot 10^{-3}$ |
| configuration finale : tous les blocs            | 456        | **0,8276** | $1{,}81 \cdot 10^{-3}$ |
| palier 1 : max-tree + min-tree + remontée        | 564        | 0,8191     | $1{,}45 \cdot 10^{-3}$ |

: Classement par ratio brut décroissant, extrait de `report/assets/ratio.md`, où figure aussi le tableau complet. Le meilleur Dice est en gras et arrive avant-dernier au ratio. \label{tab:ratio}

Nous utilisons donc deux autres cadrages, qui apparaissent tous deux en \secref{sec:resultats}.
Le premier est le front de Pareto dans le plan (nombre de paramètres, Dice), en abscisse
logarithmique, où nos configurations et les entrées publiées du challenge sont placées côte
à côte ; c'est le seul cadrage qui rende visible un compromis au lieu de le résumer par un
quotient. Le second est la comparaison d'ordre de grandeur : les méthodes du challenge
emploient de [[CHIFFRE:params_publies_min]] à [[CHIFFRE:params_publies_max]] paramètres là
où nous en avons quelques centaines. Enfin, à l'intérieur de notre propre famille de
configurations, aucune différence de Dice n'est affirmée sans comparaison appariée sur les
mêmes dix sujets, avec test de Wilcoxon, taille d'effet et nombre de sujets améliorés,
selon le protocole de la \secref{sec:protocole}.

# Méthode {#sec:methode}

## Principe

La segmentation est traitée comme une classification voxel par voxel. Chaque voxel du
masque cérébral devient une ligne d'un tableau, décrite par des colonnes calculées à la
volée sur le sujet lui-même, et un classifieur minuscule lit cette ligne pour prédire un
tissu. Le principe qui gouverne toute la construction tient en une phrase : tout ce qui se
recalcule sur le sujet courant est gratuit, tout ce qui se mémorise du jeu d'entraînement
coûte.

Ce principe a une conséquence libératrice. Un descripteur peut être aussi élaboré qu'on le
veut — une convolution multi-échelle, une transformée de distance, un arbre hiérarchique
complet — sans rien coûter au décompte, du moment qu'il se recalcule intégralement sur le
sujet qu'on est en train de segmenter et qu'il ne transporte aucune valeur issue des autres
sujets. Ce qui coûte, c'est uniquement ce qu'il faudrait sérialiser pour segmenter un
nouveau sujet. Dans notre pipeline, une seule étape est dans ce cas. La
\figref{fig:pipeline} la met en évidence.

\begin{figure}[t]
\centering
\includegraphics[width=\linewidth]{report/assets/fig02_pipeline.pdf}
\caption{Le pipeline de la configuration finale. Les six blocs de descripteurs produisent
151 colonnes par voxel, toutes recalculées sur le sujet courant. La standardisation des
colonnes est elle aussi intra-sujet. Seule la régression logistique mémorise quelque chose
du jeu d'entraînement, et c'est elle seule qui compte au décompte des paramètres.}
\label{fig:pipeline}
\end{figure}

## Les six blocs de descripteurs

Chaque bloc est présenté par l'information qui manque aux précédents. Aucun n'a de
paramètre appris, ce que la suite de tests vérifie mécaniquement (\secref{sec:protocole}).

**A — intensités (6 colonnes).** Ce que la \figref{fig:isointense} établit, c'est qu'aucune
modalité ne sépare seule. Ce qui sépare un peu mieux, c'est leur comportement conjoint : le
couple $(\mathrm{T1}, \mathrm{T2})$ recouvre à $0{,}615 \pm 0{,}027$ contre $0{,}701$ pour
le T1 seul et $0{,}867$ pour le T2 seul. Le gain est réel et il est modeste. Le bloc livre
donc six colonnes que le classifieur lit ensemble : les deux modalités z-scorées dans le
masque, leurs rangs percentiles, leur différence, et un ratio normalisé. Le ratio ne sert pas à séparer
seul : mesuré avec le même estimateur, il recouvre à $0{,}831$, donc davantage que le T1
pris isolément. Il fournit une coordonnée normalisée par sujet, que le classifieur croise
avec les cinq autres colonnes. La normalisation par la médiane intra-masque de chaque modalité,
avant le ratio, n'est pas cosmétique : le gain d'acquisition varie d'un sujet à l'autre et
d'une modalité à l'autre, et un ratio sur intensités brutes s'effondre sur le sujet 7.

**B — gaussiennes (68 colonnes).** Une intensité ne dit rien de la forme locale du signal.
Un voxel au sommet d'une crête, un voxel dans une nappe fine et un voxel au milieu d'un
bloc homogène peuvent avoir la même valeur. Ce bloc décrit le voisinage à cinq échelles,
$\sigma \in \{0{,}5,\ 1,\ 2,\ 4,\ 8\}$ mm : lissage, norme du gradient et laplacien
normalisés en échelle, valeurs propres de la hessienne triées par module croissant, et
différences de gaussiennes entre échelles consécutives. Le tri des valeurs propres rend le
descripteur invariant par rotation. Au bord du masque, la convolution est normalisée par le
masque lissé, sinon la marche entre le cerveau et le vide serait lue par les dérivées comme
une structure anatomique.

**C — spatial (9 colonnes).** La position dans le crâne est un a priori anatomique gratuit,
et les blocs précédents l'ignorent. Le liquide céphalo-rachidien occupe la périphérie et les
ventricules ; les proportions de tissus varient fortement du centre vers le cortex. Le bloc
fournit les coordonnées normalisées par la boîte englobante du masque, la distance
euclidienne au bord du masque, la distance au plan sagittal médian, et des coordonnées
sphériques autour du centroïde. Le plan médian et les axes sont estimés par analyse en
composantes principales des coordonnées des voxels du masque du sujet. Tout est relatif au
sujet : ni atlas, ni recalage, ni valeur transportée.

**D — morphologie (52 colonnes).** Les trois blocs précédents sont locaux. Aucun ne peut
exprimer qu'un voxel appartient à une région mince enveloppant une région beaucoup plus
grande. C'est l'objet de la \secref{sec:tos}.

**E — symétrie (4 colonnes).** Le point controlatéral est une information que rien
d'autre n'apporte. Le cerveau est presque symétrique par rapport au plan sagittal médian, et
un voxel et son miroir appartiennent le plus souvent au même tissu. Une asymétrie locale
d'intensité signale donc une frontière ou une structure impaire, comme les ventricules ou la
scissure interhémisphérique. Le bloc donne, pour chaque modalité z-scorée, l'intensité au
point miroir par interpolation trilinéaire et l'écart entre le voxel et son miroir. Le plan
est celui du bloc C.

**F — contexte (12 colonnes).** Il reste à décrire le voisinage immédiat pour un coût
négligeable. Le bloc calcule la moyenne et l'écart-type locaux des rangs percentiles des
deux modalités, dans des boîtes de rayon 1, 2 et 4 voxels, normalisés par le masque pour ne
pas être biaisés au bord. Il lisse les données, et non des probabilités apprises : c'est ce
qui le distingue de l'auto-contexte de la \secref{sec:classifieur}, et ce qui le rend
gratuit.

## Arbre des formes et remontée de branche {#sec:tos}

Les blocs A à C lisent tous un voisinage de quelques millimètres au plus. Or à six mois la
frontière entre substance grise et substance blanche ne se voit pas localement : c'est
exactement ce que la \figref{fig:isointense} mesure. Ce qui distingue un ruban cortical de
la substance blanche sous-jacente n'est pas le contraste local, c'est le fait que le ruban
est une forme mince enveloppant une forme beaucoup plus grande. C'est un énoncé sur
l'inclusion des régions les unes dans les autres, à toutes les échelles, et aucun filtre
local ne sait l'exprimer.

L'arbre des formes est la structure qui l'exprime. On seuille l'image à tous les niveaux,
dans les deux sens, et on sature les composantes obtenues en bouchant leurs trous. Ces
formes saturées ne se croisent jamais : deux d'entre elles sont disjointes ou emboîtées.
Elles s'organisent donc en un arbre unique dont la racine est l'image entière
[@monasse2000fast], et que l'on sait calculer en temps quasi linéaire en dimension
quelconque [@geraud2013quasilinear]. Chaque voxel appartient à une branche complète, de la
plus petite forme qui le contient jusqu'à la racine. La \figref{fig:tos} montre
l'emboîtement et l'arbre correspondant sur une image de synthèse, calculés par higra
[@perret2019higra] avec la même fonction que celle utilisée en trois dimensions.

\begin{figure}[t]
\centering
\includegraphics[width=\linewidth]{report/assets/fig03_shapes.pdf}
\caption{Arbre des formes d'une image de synthèse à cinq niveaux, calculé et non dessiné à
la main. (a)~Les formes saturées, en pointillé blanc, et en trait plein la branche du voxel
$p$. (b)~L'arbre d'inclusion, avec en ordonnée l'aire des nœuds en échelle logarithmique et
en accent la branche de $p$. Le remplissage d'un nœud rappelle le niveau de gris de la
forme correspondante : la forme sombre est emboîtée entre deux formes claires sur la même
branche, ce qu'aucun max-tree ni min-tree ne produirait. Les lignes horizontales sont les
seuils d'aire ; le premier ancêtre $a(T_i)$ de la remontée de branche est le premier nœud de
la branche situé au-dessus de la ligne $T_i$.}
\label{fig:tos}
\end{figure}

L'arbre des formes est auto-dual : l'arbre de $f$ et celui de $-f$ sont le même. Une forme
sombre incluse dans une forme claire est un nœud au même titre qu'une forme claire incluse
dans une forme sombre, ce que la \figref{fig:tos} illustre. La propriété nous sert
directement, parce que le T1 et le T2 ont des contrastes inversés et qu'un seul arbre par
modalité les décrit de la même façon. La solution de repli, un max-tree accompagné d'un
min-tree [@salembier1998antiextensive], demande deux arbres et deux fois plus de colonnes
pour les mêmes attributs.

Il faut être précis sur ce que nous conservons et ce que nous abandonnons. L'arbre des
formes théorique est invariant à toute transformation croissante de l'intensité. Nous ne
conservons pas cette invariance. Nous quantifions l'image sur 256 niveaux répartis
linéairement entre les percentiles 1 et 99 intra-masque. Sous une transformation affine de
l'intensité, gain et décalage d'acquisition, ces percentiles se transforment de la même
façon, l'image quantifiée est identique et tout ce qui en découle l'est aussi : l'invariance
affine est exacte. Sous une transformation croissante quelconque, une correction gamma par
exemple, les classes de quantification ne coïncident plus avec les lignes de niveau, et les
attributs qui lisent des altitudes — contraste, dynamique, résidu — changent. La variante
qui conserve cette invariance, une quantification par rang percentile, existe dans le code
et nous l'avons mesurée en leave-one-out : elle perd $0{,}0018$ de Dice moyen, avec 2 sujets
améliorés sur 10 et $p = 0{,}064$, ce qui ne la distingue pas du bruit
(\secref{sec:resultats}). Nous gardons la quantification linéaire parce que les volumes
iSeg sont déjà corrigés en inhomogénéité de champ, ce qui rend l'invariance non linéaire peu
utile ici, et parce que les niveaux linéaires préservent les amplitudes de contraste que les
attributs exploitent. Nous revendiquons donc l'auto-dualité et l'invariance affine, et nous
ne revendiquons pas l'invariance au contraste.

Chaque nœud de l'arbre porte six attributs sans dimension, du même genre que ceux des
filtres par attribut [@breen1996attribute] : le logarithme de son aire
rapportée au volume du masque, sa profondeur normalisée, son contraste au parent, sa
dynamique, sa sphéricité et son extension. La dynamique est définie comme l'étendue des
niveaux de la sous-arborescence, et non par la hauteur signée usuelle, qui dépend du sens du
contraste et casserait l'auto-dualité ; les tests le vérifient.

La remontée de branche est notre contribution propre. Le nœud propre d'un voxel, la plus
petite forme qui le contient, reste un objet local : pour un voxel cortical, c'est un
fragment de gyrus. L'information utile est plus haut dans la branche. Nous fixons donc
quatre seuils d'aire — $100$, $1\,000$, $10\,000$ et $100\,000$ voxels — et, pour chacun, nous
remontons la branche du voxel jusqu'au premier ancêtre dont l'aire atteint le seuil, dont
nous lisons cinq attributs. Avec les six attributs du nœud propre, cela fait
$2 \times (6 + 4 \times 5) = 52$ colonnes pour les deux modalités. Le voxel dispose ainsi
d'une description de son contexte à quatre échelles anatomiques, du fragment de gyrus au
lobe entier, pour zéro paramètre appris : les seuils sont fixés a priori et les ancêtres
sont lus sur l'arbre du sujet lui-même.

Le calcul ne coûte qu'une passe sur les nœuds. Comme l'aire croît d'un nœud vers son parent,
le premier ancêtre d'aire suffisante obéit à la récurrence
$$a_T(n) = \begin{cases} n & \text{si } \mathrm{aire}(n) \ge T \\ a_T(\mathrm{parent}(n)) & \text{sinon} \end{cases}$$
qui se résout pour tous les nœuds à la fois, par sauts de pointeurs vectorisés, en un temps
linéaire en nombre de nœuds. Le coût ne dépend ni du nombre de voxels par nœud ni de la
profondeur de l'arbre. La \figref{fig:tos}b se lit directement comme cette récurrence :
l'ordonnée étant l'aire, l'ancêtre retenu pour un seuil est simplement le premier nœud de la
branche au-dessus de la ligne du seuil.

La remontée de branche apporte, à structure d'arbre identique, $+0{,}0035$ de Dice moyen sur
la variante qui ne lit que le nœud propre, avec 10 sujets améliorés sur 10 et
$p = 0{,}002$. Le bloc morphologique dans son ensemble apporte $+0{,}0102$ sur la
configuration sans morphologie, également sur 10 sujets sur 10. Le détail est en
\secref{sec:resultats}.

## Classifieur et post-traitement {#sec:classifieur}

Paragraphe à rédiger. Modèles, auto-contexte [@tu2010autocontext] et sa validation croisée
interne, contraintes topologiques, sélection de features.

## Convention de comptage des paramètres

Paragraphe à rédiger, avec l'encadré de la convention et le chiffre selon la convention
inverse.

# Protocole expérimental {#sec:protocole}

Section à rédiger. Leave-one-out à dix plis, contrôle anti-fuite, métriques Dice / ASD /
MHD, protocole statistique.

# Résultats {#sec:resultats}

Section à rédiger. Tableau d'ablation, front de Pareto, budget de frugalité, figures
qualitatives.

# Discussion

Section à rédiger.

# Conclusion

Section à rédiger.

<!--
================================================================================
MARQUEURS RESTANTS — à remplacer depuis report/assets/facts.md ou un JSON de
results/ avant le rendu final. Ne jamais y écrire une valeur provisoire.

  [[NOM:arthur]]               nom de famille d'Arthur, page de titre
  [[RÉSUMÉ]]                   résumé, à écrire en dernier
  [[CHIFFRE:dice_final]]       § 1, Dice moyen de la configuration finale figée
  [[CHIFFRE:parametres_final]] § 1, paramètres de la configuration finale figée
  [[CHIFFRE:params_publies_min]] § 2, borne basse des paramètres des méthodes publiées
  [[CHIFFRE:params_publies_max]] § 2, borne haute des paramètres des méthodes publiées

À REGÉNÉRER quand la configuration finale sera figée :
  tableau 1 (§ 2)  <- make report-assets puis python scripts/ratio_argument.py
================================================================================
-->
