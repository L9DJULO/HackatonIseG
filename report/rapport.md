---
title: "Segmentation frugale des IRM cérébrales de nourrissons en phase isointense"
subtitle: "Hackathon SCIA 2026 — sujet 2, challenge MICCAI iSeg-2017"
author:
  - Jules Lange
  - "Arthur Goullet De Rugy"
date: "septembre 2026"
abstract: |
  À six mois, la myélinisation est à mi-course et substance grise et substance blanche ont
  presque la même intensité : aucune méthode fondée sur la valeur d'un point ne peut
  fonctionner. Nous segmentons les trois tissus des IRM T1 et T2 du challenge MICCAI iSeg-2017
  en déplaçant l'information des poids appris vers des descripteurs non appris et non locaux —
  au premier rang desquels un arbre des formes tridimensionnel auto-dual, dont on remonte la
  branche de chaque voxel vers ses ancêtres à quatre échelles d'aire — puis en les donnant à une
  régression logistique à deux étages reliés par de l'auto-contexte. En leave-one-out sur les
  dix sujets annotés, cette configuration atteint un Dice moyen de 0,8399 pour 939 paramètres
  appris, et une variante à 163 paramètres en atteint encore 0,8036 ; la méthode classée
  première du challenge emploie 1,55 million de paramètres. Nous montrons pourquoi le rapport
  brut du Dice au nombre de paramètres ne peut pas servir de critère de sélection, nous lui
  substituons un front de Pareto et une comparaison en ordres de grandeur. Notre décompte est
  exact, sa règle est écrite et nous donnons le chiffre selon la convention inverse : c'est
  cette rigueur qui autorise la lecture grossière, et non le contraire. Nous rapportons enfin
  trois résultats négatifs : l'auto-dualité
  de l'arbre des formes ne produit aucun gain de Dice distinguable, notre post-traitement
  topologique dégrade la segmentation parce qu'il repose sur une hypothèse anatomique fausse aux
  ventricules, et la quantification à 64 niveaux ne fait économiser rien de mesurable. Nos
  chiffres sont un leave-one-out sur dix sujets et ne sont pas directement comparables aux
  scores publiés du challenge, qui sont calculés sur treize autres sujets.
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
grise, dont le recouvrement vrai vaut 1, il rend $0{,}991$. L'écart est donc réel.

La conséquence est directe. Sur un problème à deux classes d'effectifs égaux, la meilleure
règle de décision concevable fondée sur la seule intensité d'un voxel se trompe sur la
moitié de l'aire de recouvrement : son exactitude plafonne à 65,0 % en T1 et à 56,6 % en
T2. Même en lisant les deux modalités conjointement, le plafond monte seulement à 69,3 %.
Aucune méthode fondée sur la valeur d'un point ne peut fonctionner ici. L'information
doit venir d'ailleurs : de la géométrie locale, de la position anatomique, et de la façon
dont les régions s'emboîtent les unes dans les autres.

\begin{figure}[t]
\centering
\includegraphics[width=0.96\linewidth]{report/assets/fig01_isointense.pdf}
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

Ce rapport défend une seule affirmation, et chaque section y contribue : sur la segmentation
de cerveaux de nourrissons en phase isointense, on atteint une fraction substantielle du
Dice des méthodes publiées avec trois à quatre ordres de grandeur moins de paramètres, en
déplaçant l'information des poids appris vers des descripteurs géométriques et
hiérarchiques calculés à la volée. Notre configuration la plus performante, celle qui ajoute
l'auto-contexte décrit en \secref{sec:classifieur}, obtient un Dice moyen de $0{,}8399$ pour
**939 paramètres appris** ; la plus frugale de notre famille en obtient $0{,}8036$ pour 163. La
méthode classée première du challenge en emploie un million et demi.

La \secref{sec:probleme} pose les données, la limite d'évaluation qu'elles imposent, et
montre pourquoi le rapport brut du Dice au nombre de paramètres ne peut pas servir à choisir
une configuration. La \secref{sec:methode} décrit les six blocs de descripteurs, l'arbre des
formes, le classifieur et la convention de comptage. Suivent le protocole, les résultats et la
discussion.

# Position du problème et métrique {#sec:probleme}

Le jeu iSeg-2017 comprend dix sujets annotés et treize sujets sans annotation publique.
Chaque sujet fournit un volume T1 et un volume T2 de $144 \times 192 \times 256$ voxels de
1 mm isotrope, et, pour les dix premiers, une carte de référence à trois tissus tracée
manuellement. La conséquence est immédiate et nous l'assumons : toute notre évaluation est
un leave-one-out sur dix sujets, et il n'existe pas de jeu de test externe. Les treize
sujets restants ne servent qu'à des figures qualitatives, faute de vérité terrain. Nos
chiffres ne sont donc pas directement comparables aux scores publiés du challenge, qui sont
calculés par le serveur d'évaluation sur ces treize sujets.

Le quotient du Dice par le nombre de paramètres se calcule vite, et il ne peut pas servir à
choisir une configuration. Le Dice est borné par 1 et sature, comme le montre notre propre
front en \figref{fig:pareto} ; le dénominateur, lui, croît sans limite. Le quotient est donc
maximisé par le plus petit modèle de la liste, quelle que soit sa qualité.

Nous avons fait le calcul sur nos propres configurations plutôt que de le supposer. Le ratio
brut y varie d'un facteur 5,5 quand le Dice ne varie que d'un facteur 1,05 : il mesure la
taille du modèle et presque rien d'autre. Le \tabref{tab:ratio} le montre. Celle de nos
configurations qui obtient le meilleur ratio brut est aussi celle qui a le plus mauvais Dice,
la sélection à 40 colonnes à $0{,}8036$ ; celle qui a le meilleur Dice, $0{,}8399$, arrive
dernière. Et le classement est dominé par un modèle qui ne segmente rien. Le classifieur
dégénéré mémorise un seul nombre, l'indice du tissu majoritaire des neuf sujets
d'entraînement ; il obtient un Dice moyen de $0{,}2139 \pm 0{,}0082$, un ratio 43 fois
supérieur au meilleur ratio réel et 239 fois supérieur à celui de notre meilleure
configuration. Un classement qui place ce modèle premier ne sélectionne rien.

| rang | configuration | param. | tranche | Dice moyen | Dice / param. |
|-----:|:-------------------------------------------|-----------:|:------:|----------:|------------:|
| 1  | classifieur dégénéré : majoritaire | 1 | $10^{0}$ | 0,2139 | $2{,}14 \cdot 10^{-1}$ |
| 2  | sélection des 40 meilleures colonnes | 163 | $10^{2}$ | 0,8036 | $4{,}93 \cdot 10^{-3}$ |
| 3  | A+B+C, sans morphologie (référence) | 252 | $10^{2}$ | 0,8055 | $3{,}20 \cdot 10^{-3}$ |
| 4  | palier 0 : max-tree + min-tree | 324 | $10^{2}$ | 0,8156 | $2{,}52 \cdot 10^{-3}$ |
| 5  | palier 2 : arbre des formes + remontée | 408 | $10^{2}$ | 0,8154 | $2{,}00 \cdot 10^{-3}$ |
| 9  | configuration finale : tous les blocs | 456 | $10^{2}$ | 0,8276 | $1{,}81 \cdot 10^{-3}$ |
| 12 | palier 1 : les deux arbres + remontée | 564 | $10^{2}$ | 0,8191 | $1{,}45 \cdot 10^{-3}$ |
| 13 | finale + auto-contexte | 939 | $10^{2}$ | **0,8399** | $8{,}94 \cdot 10^{-4}$ |
|    | MSL\_SKKU, 1\textsuperscript{re} du challenge | $1{,}55 \cdot 10^{6}$ | $10^{6}$ | 0,9283 | $5{,}99 \cdot 10^{-7}$ |

: Classement par ratio brut décroissant, extrait de `report/assets/ratio.md` où figurent les
treize configurations. Le meilleur Dice est en gras et arrive dernier ; le meilleur ratio réel
est celui du plus mauvais Dice. La colonne « tranche » est la puissance de dix du décompte :
elle ne distingue pas 163 de 939 et distingue franchement $10^2$ de $10^6$. La dernière ligne
combine le Dice publié par le serveur du challenge et un compte de paramètres publié
[@wang2019iseg] ; elle n'est pas évaluée sur les mêmes sujets que les nôtres, et son Dice moyen
est la moyenne des trois tissus officiels. \label{tab:ratio}

La lecture en ordres de grandeur ne fait pas la même erreur, et c'est parce qu'elle est plus
grossière. Elle ne compare que la tranche. Nos douze configurations réelles y tombent toutes
dans la même, $10^2$, de 163 à 939 paramètres : elle ne les départage pas, et n'a pas à le
faire — à l'intérieur d'une tranche, c'est le Dice qui décide, et il désigne l'auto-contexte.
Elle ne parle que lorsque la tranche change. C'est le cas deux fois : contre les méthodes
publiées du challenge, en $10^6$ et $10^7$, quatre à cinq tranches au-dessus ; et contre le
classifieur dégénéré, deux tranches en dessous, que son Dice de $0{,}21$ élimine aussitôt.
Aucun ratio brut ne le faisait.

Elle ne répare pas tout. Elle ne classe rien à l'intérieur d'une tranche, donc elle ne peut pas
servir seule : elle dit seulement où poser la question du Dice. Nous ne présentons jamais une
tranche sans le Dice qui l'accompagne.

Deux cadrages en découlent, et tous deux apparaissent en \secref{sec:resultats}. Le premier est
le front de Pareto dans le plan (nombre de paramètres, Dice), en abscisse logarithmique, où nos
configurations et les entrées publiées du challenge sont placées côte à côte ; c'est le seul
qui rende visible un compromis au lieu de le résumer par un quotient. Le second est la
comparaison d'ordre de grandeur, faite sur les deux seules méthodes du challenge dont le nombre
de paramètres est publié. MSL\_SKKU, classée première, « a 47 couches et 1,55 million de
paramètres appris » selon l'article de synthèse du challenge [@wang2019iseg]. HyperDenseNet en
compte $10\,349\,450$, dont $9\,518\,850$ de convolution, d'après le tableau de comptage de ses
auteurs [@dolz2019hyperdensenet]. Nous en avons quelques centaines à un millier : trois à
quatre ordres de grandeur de moins. Aucun autre compte n'est avancé, ni dans le texte ni sur le
front de Pareto, parce qu'il faudrait l'estimer. La comparaison est en ordre de grandeur ;
notre décompte, lui, est exact, et la \secref{sec:comptage} en donne la règle et le chiffre
selon la convention inverse.

À l'intérieur de notre propre famille de configurations, enfin, aucune différence de Dice n'est
affirmée sans comparaison appariée sur les mêmes dix sujets, avec test de Wilcoxon, taille
d'effet et nombre de sujets améliorés, selon le protocole de la \secref{sec:protocole}.

# Méthode {#sec:methode}

## Principe

La segmentation est traitée comme une classification voxel par voxel. Chaque voxel du
masque cérébral devient une ligne d'un tableau, décrite par des colonnes calculées à la
volée sur le sujet lui-même, et un classifieur minuscule lit cette ligne pour prédire un
tissu. Le principe qui gouverne toute la construction tient en une phrase : tout ce qui se
recalcule sur le sujet courant est gratuit, tout ce qui se mémorise du jeu d'entraînement
coûte.

Un descripteur peut alors être aussi élaboré qu'on le veut. Une convolution multi-échelle,
une transformée de distance, un arbre hiérarchique complet : rien de tout cela ne coûte au
décompte, du moment que le calcul se refait intégralement sur le sujet qu'on segmente et ne
transporte aucune valeur venue des autres. Ce qui coûte, c'est ce qu'il faudrait sérialiser
pour segmenter un nouveau sujet. Une seule étape de notre pipeline est dans ce cas, et la
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
masque, leurs rangs percentiles, leur différence, et un ratio normalisé. Le ratio ne sépare pas seul : mesuré
avec le même estimateur, il recouvre à $0{,}831$, davantage que le T1 pris isolément. Il sert
de coordonnée normalisée par sujet, que le classifieur croise avec les autres colonnes. C'est
la normalisation par la médiane intra-masque qui rend ce ratio comparable d'un sujet à l'autre,
le gain d'acquisition variant d'une acquisition à la suivante.

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
attributs qui lisent des altitudes — contraste, dynamique, résidu — changent.

La variante
qui conserve cette invariance, une quantification par rang percentile, existe dans le code et
nous l'avons mesurée en leave-one-out : elle perd $0{,}0018$ de Dice moyen, 2 sujets améliorés
sur 10, $p = 0{,}322$ après Holm. Elle ne se distingue donc pas du bruit
(\secref{sec:resultats}), et rien ne nous obligeait à trancher. Nous avons gardé la
quantification linéaire, dont nous supposons, sans l'avoir vérifié, qu'elle sert les attributs
d'altitude en préservant les amplitudes de contraste. Nous revendiquons l'auto-dualité et
l'invariance affine ; nous ne revendiquons pas l'invariance au contraste.

Chaque nœud de l'arbre porte six attributs sans dimension, du même genre que ceux des
filtres par attribut [@breen1996attribute] : le logarithme de son aire
rapportée au volume du masque, sa profondeur normalisée, son contraste au parent, sa
dynamique, sa sphéricité et son extension. Pour la dynamique nous prenons l'étendue des
niveaux de la sous-arborescence : la hauteur usuelle est signée par le sens du contraste, ce
qui casserait l'auto-dualité. Un test le vérifie.

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

Le classifieur est une régression logistique multinomiale. À $F$ colonnes elle coûte
exactement $3(F+1)$ poids, soit 456 pour les 151 colonnes de la configuration finale. Deux
raisons à ce choix. Elle combine linéairement des descripteurs d'échelles et d'unités
différentes, ce qui est tout ce que nous lui demandons. Et son décompte ne se discute pas, là
où un modèle à base d'arbres obligerait à convenir d'abord de ce que coûte un nœud. La régularisation vaut $C = 1$ et le
nombre d'itérations 300, tous deux fixés a priori et jamais choisis sur les labels.
L'optimiseur en réclame 319 pour converger complètement ; l'écart a été mesuré sur un pli et
le Dice est identique à la quatrième décimale.

**L'auto-contexte, et le piège qu'il tend.** Le classifieur décide voxel par voxel. Le bloc F
lui donne déjà un voisinage, mais sur les intensités ; l'auto-contexte [@tu2010autocontext]
lui en donne un sur les décisions. Un premier étage produit une carte de probabilités, on en
lit la moyenne dans des voisinages gaussiens de 1, 2 et 4 mm, et un second étage reçoit les
colonnes d'origine plus ces neuf colonnes-là. Un voxel isolément ambigu redevient décidable
si tout ce qui l'entoure penche déjà d'un côté : c'est exactement ce qui manque en phase
isointense.

Le piège est dans l'entraînement du second étage. Si les cartes de probabilités qu'il voit
ont été produites par le premier étage sur ses propres données d'entraînement, elles sont
anormalement bonnes — le premier étage a déjà vu ces voxels. Le second apprend alors à faire
au premier une confiance que la qualité réelle ne justifie pas, et l'ensemble se dégrade à
l'inférence. La parade est une validation croisée interne aux neuf sujets d'entraînement du
pli courant : les colonnes de contexte d'un sujet sont toujours produites par un modèle qui
ne l'a jamais vu. Le sujet laissé dehors par la boucle externe n'entre nulle part, et la
partition interne ne concerne que les neuf autres.

Ce que cela coûte est explicite : les deux étages sont transportés à l'inférence, soit
$3(F+1) + 3(F+10)$ paramètres, 939 pour $F = 151$. Les modèles des plis internes, eux, sont
jetés une fois les colonnes de contexte fabriquées ; ils ne sont pas transportés et ne
comptent pas. C'est le seul point de la convention où un lecteur pourrait vouloir trancher
autrement, et il est écrit ici pour qu'il puisse le faire.

**Le post-traitement, à zéro paramètre.** Trois défauts découlent mécaniquement d'une
décision prise voxel par voxel : du bruit poivre-et-sel dans les régions homogènes, des
composantes minuscules isolées, et des contacts directs entre substance blanche et liquide
céphalo-rachidien. Le dernier est le plus intéressant, parce qu'il est anatomiquement
impossible : le ruban cortical s'interpose partout entre les deux. Trois étapes les
corrigent — lissage gaussien des probabilités à $\sigma = 1$ mm en convolution normalisée,
suppression des composantes connexes de moins de 30 mm³ avec réattribution à la meilleure
classe suivante, et interdiction de toute 6-adjacence entre substance blanche et LCR, le
voxel le moins sûr des deux passant en matière grise. Aucun de ces seuils n'est calibré sur
les labels : ils viennent de l'échelle du voxel et de l'anatomie. Le post-traitement ajoute
donc zéro paramètre appris. Un seuil calibré sur les labels d'entraînement, lui, devrait être
compté.

**La sélection de colonnes n'est pas gratuite.** On peut ne garder que les $K$ colonnes de
plus grand poids et réajuster. Le décompte passe alors de $3(F+1)$ à $3(K+1) + K$, car les
indices retenus sont ajustés sur les sujets d'entraînement et doivent être transportés : sans
eux, on ne sait pas quelles colonnes présenter au modèle. Ils tombent donc sous la règle de
la \secref{sec:comptage} et sont comptés, un entier par colonne. À $K = 40$, cela fait 163
paramètres contre 456 : c'est le gain net, et il est plus modeste que la seule réduction du
nombre de poids ne le laisserait croire.

**Ce que les trois donnent.** Un seul des trois gagne. L'auto-contexte porte le Dice de
$0{,}8276$ à $0{,}8399$, sur les dix sujets. La sélection à 40 colonnes coûte $-0{,}0240$ de
Dice et divise le décompte par 2,8, ce qui en fait un point du front de Pareto plutôt qu'un
échec. Le post-traitement dégrade : $-0{,}0031$ pour le lissage et le nettoyage, $-0{,}0011$
de plus pour la contrainte topologique. La \secref{sec:resultats} donne les chiffres complets
et la \secref{sec:discussion} dit pourquoi le post-traitement échoue.

Les trois mécanismes sont couverts par la suite de tests, dont un test d'intégration qui fait
tourner la boucle leave-one-out complète sur des sujets de synthèse.

## Convention de comptage des paramètres {#sec:comptage}

\begin{encadre}{Ce qui compte comme paramètre appris}
\textbf{La règle.} Est un paramètre appris toute quantité ajustée sur les sujets
d'entraînement et réutilisée telle quelle à l'inférence — autrement dit, toute quantité qu'il
faudrait sérialiser pour segmenter un nouveau sujet.

\smallskip
\textbf{Comptent :} les poids et les biais du classifieur, sans exception, et pour chaque
étage s'il y en a plusieurs ; les indices des colonnes retenues par une sélection ; toute
statistique de normalisation estimée sur le train et figée ; tout seuil de post-traitement
qui serait calibré sur les labels.

\smallskip
\textbf{Ne comptent pas :} les statistiques recalculées sur le sujet courant à l'inférence,
z-score et médiane intra-masque, rangs percentiles, moyenne et écart-type par colonne ; les
hyperparamètres fixés a priori, sigmas des gaussiennes, seuils d'aire de l'arbre des formes,
niveaux de quantification, rayons de voisinage, seuils du post-traitement ; la structure des
descripteurs elle-même, dont la suite de tests vérifie mécaniquement qu'aucun n'a de
paramètre appris.
\end{encadre}

Le point qui décide de tout est la standardisation. Elle est intra-sujet : la moyenne et
l'écart-type de chaque colonne sont recalculés sur le masque cérébral du sujet qu'on est en
train de segmenter, à l'entraînement comme à l'inférence. Elle ne mémorise donc rien du jeu
d'entraînement, et segmenter un nouveau sujet ne demande de transporter aucune de ces
valeurs : c'est le même statut qu'un filtre gaussien ou qu'un calcul d'aire.

Un jury peut être en désaccord avec cette frontière, et il doit trouver son propre chiffre ici
plutôt que d'avoir à le reconstituer. **Selon la convention inverse, où le scaler serait compté,
la configuration finale passe de 456 à 758 paramètres** : $2 \times 151$ valeurs de plus, une
moyenne et un écart-type par colonne. Les deux nombres sont des décomptes exacts, pas des
estimations : 456 est $3 \times (151 + 1)$, 758 est $456 + 2 \times 151$, et un test recompte
les deux à chaque exécution.

Et c'est ici que la lecture en ordres de grandeur retenue en \secref{sec:probleme} montre son
second mérite. **Changer de convention déplace le ratio brut de $-40$ \%. Il ne déplace pas la
tranche du tout** : 456 et 758 sont l'un et l'autre à quelques centaines, tranche $10^2$. La
lecture est grossière parce que les deux comptes sont exacts et qu'ils tombent dans la même
tranche — pas parce que le décompte serait incertain. Un désaccord sur la frontière entre « paramètre appris » et
« opération » ferait donc basculer un classement fondé sur le ratio brut, et ne changerait
rigoureusement rien à un classement fondé sur les ordres de grandeur. Dans les deux cas, quatre
tranches séparent notre modèle du million et demi de paramètres de la méthode classée
première. Nous ne demandons donc à personne d'adhérer à notre frontière.

# Protocole expérimental {#sec:protocole}

**Leave-one-out.** Dix plis sur les dix sujets annotés. Neuf sujets entraînent, le dixième est
segmenté entièrement. Graines fixées, celle de l'échantillonnage dérivée du numéro du sujet de
test. `python -m src.cli run experiments/<config>.yaml` reproduit n'importe quel résultat du
rapport et écrit un JSON dans `results/`. Tous les chiffres en viennent par
`make report-assets`. Aucun n'est recopié à la main.

**Le contrôle anti-fuite.** La propriété la plus critique du protocole, et la seule que nous
ayons refusé de confier à une relecture. Chaque bloc est calculé trois fois sur le même sujet :
avec la vraie carte de labels, avec une carte permutée, et sans aucune carte, comme sur les
treize sujets de test. Le test exige les trois sorties identiques bit à bit. Un bloc qui lirait
la vérité terrain, même indirectement, échoue. Un second test vérifie qu'aucun bloc ne garde
d'état d'un sujet au suivant.

**Métriques.** Les trois du challenge, toutes rapportées : Dice, distance de surface moyenne
(ASD), distance de Hausdorff modifiée (MHD, 95\textsuperscript{e} percentile des distances de
surface symétriques). Par classe et par sujet, jamais agrégées sur les voxels de plusieurs
sujets. Le fond n'est jamais évalué. Le Dice mesure un volume, les distances une frontière, et
une configuration peut gagner sur l'un en perdant sur l'autre. C'est le cas du lissage.

**Statistiques.** Dix sujets, c'est peu. Le même sujet passant dans toutes les configurations,
toutes les comparaisons sont appariées. Chacune rapporte le delta moyen, son écart-type
inter-sujets, le test des rangs signés de Wilcoxon bilatéral, deux tailles d'effet — $d$ de
Cohen apparié et $\delta$ de Cliff — et le nombre de sujets améliorés sur dix. Ce dernier
mérite sa justification : à $n = 10$ l'amplitude d'un gain est bruitée, sa systématicité ne
l'est pas. Un effet est déclaré distinguable du bruit si la p-valeur ajustée descend sous 0,05
**et** si au moins huit sujets sur dix vont dans le même sens. La règle est symétrique : une
dégradation systématique reste un résultat.

Les quatorze comparaisons forment une liste fixe, écrite dans `scripts/report_assets.py` avant
lecture des p-valeurs. Holm porte sur la famille entière ; corriger sur un sous-ensemble serait
plus permissif. À $n = 10$ la plus petite p-valeur atteignable vaut 0,002, soit 0,027 après
correction, et tous les gains que nous revendiquons la franchissent. Elle nous coûte un
résultat, un seul : la dégradation à 64 niveaux, distinguable avant correction, ne l'est plus
après (\secref{sec:resultats}).

# Résultats {#sec:resultats}

Toutes les valeurs de cette section viennent de `report/assets/`, régénéré depuis les JSON de
`results/` par `make report-assets`. Aucune n'est écrite à la main.

## Ablation

Le \tabref{tab:ablation} donne les douze configurations. Trois choses s'y lisent.

**Le contexte non local paye, la description locale plafonne.** Passer de A+B+C au bloc
morphologique gagne $+0{,}0102$ de Dice, dix sujets sur dix ; la remontée de branche en ajoute
$+0{,}0035$, dix sujets sur dix également. Les deux survivent à Holm. Les raffinements
purement locaux, filtres de grain et quantification par rang, ne produisent rien de
distinguable. C'est ce que la phase isointense laissait attendre : ce qui manque au voxel
n'est pas dans son voisinage.

**L'auto-contexte prolonge le même mouvement**, sur le même principe : du contexte non local,
porté cette fois par les décisions plutôt que par les intensités. Il monte le Dice à
$0{,}8399$ et gagne sur les dix sujets. C'est le seul point du tableau à obtenir en même temps
le meilleur Dice, le meilleur ASD et le meilleur MHD.

**Deux mécanismes échouent, et nous les gardons dans le tableau.** Le post-traitement dégrade.
L'arbre des formes n'apporte rien contre la paire max-tree / min-tree. La
\secref{sec:discussion} y revient.

| configuration | param. | LCR | SG | SB | Dice moyen |
|:------------------------------------------|-------:|------:|------:|------:|-----------:|
| A+B+C, sans morphologie (référence)        | 252 | 0,851 | 0,805 | 0,761 | 0,8055 |
| palier 0 : max-tree + min-tree             | 324 | 0,866 | 0,813 | 0,767 | 0,8156 |
| palier 1 : + remontée de branche           | 564 | 0,868 | 0,818 | 0,772 | 0,8191 |
| palier 2 : arbre des formes + remontée     | 408 | 0,866 | 0,814 | 0,766 | 0,8154 |
| palier 3 : + filtres de grain              | 426 | 0,866 | 0,814 | 0,766 | 0,8154 |
| palier 2, quantification 64 niveaux        | 408 | 0,866 | 0,814 | 0,765 | 0,8149 |
| palier 2, quantification par rang          | 408 | 0,862 | 0,813 | 0,766 | 0,8136 |
| sélection des 40 meilleures colonnes       | 163 | 0,861 | 0,804 | 0,746 | 0,8036 |
| configuration finale : tous les blocs      | 456 | 0,881 | 0,825 | 0,777 | 0,8276 |
| finale + lissage et nettoyage              | 456 | 0,876 | 0,825 | 0,773 | 0,8246 |
| finale + contrainte topologique            | 456 | 0,877 | 0,823 | 0,770 | 0,8235 |
| **finale + auto-contexte**                 | **939** | **0,891** | **0,834** | **0,795** | **0,8399** |

: Ablation en leave-one-out sur les dix sujets annotés. Dice moyen par tissu ; les
écarts-types inter-sujets, qui valent de 0,009 à 0,018 selon le tissu, sont omis ici pour la
lisibilité et figurent dans `report/assets/ablation.md` avec l'ASD et la MHD. Les quatorze
comparaisons appariées sont dans `report/assets/stats.md`. \label{tab:ablation}

## Le front de Pareto

\begin{figure}[t]
\centering
\includegraphics[width=\linewidth]{report/assets/fig04_pareto.pdf}
\caption{Front de Pareto dans le plan (paramètres appris, Dice moyen), abscisse
logarithmique. Les deux références publiées sont les seules méthodes du challenge pour
lesquelles on dispose à la fois d'un Dice officiel et d'un compte de paramètres publié ;
aucune méthode dont il faudrait estimer le décompte n'est placée dans le nuage. La mise en
garde portée sur la figure n'est pas décorative : nos valeurs sont un leave-one-out sur les
dix sujets annotés, les leurs viennent du serveur des organisateurs sur les treize sujets de
test.}
\label{fig:pareto}
\end{figure}

La \figref{fig:pareto} porte l'argument central. Notre front s'étend de 163 à 939 paramètres,
et sa forme est celle qu'on attend : le Dice croît d'abord vite, puis se tasse. Rapporté à la
méthode classée première du challenge, notre meilleur point atteint **90,5 % de son Dice avec
1 651 fois moins de paramètres**. Le point le plus frugal, à 163 paramètres, en atteint encore
86,6 % avec un facteur près de dix mille.

L'énoncé qui résume la figure ne dépend d'aucun décompte fin : **nous sommes en $10^2$
paramètres là où le challenge est en $10^6$ et $10^7$, pour un Dice qui vaut environ 90 % du
sien.** C'est le seul sens dans lequel nous faisons mieux. En Dice absolu nous sommes derrière,
et à l'intérieur de notre propre tranche, c'est le Dice qui désigne l'auto-contexte.

Ces pourcentages se lisent en ordre de grandeur et pas autrement : les deux nuages ne sont pas
évalués sur les mêmes sujets, et nous n'avons pas soumis au serveur du challenge.

## Ce que valent les intervalles, et ce que valent les tests

\begin{figure}[t]
\centering
\includegraphics[width=0.96\linewidth]{report/assets/fig05_ablation.pdf}
\caption{Ablation en barres. (a)~Dice absolu de chaque configuration, intervalle de confiance
à 95 \% de la moyenne sur les dix sujets : tous les intervalles se chevauchent. (b)~Delta
apparié contre l'étape précédente : la variabilité inter-sujets s'annule dans la différence et
des effets nets apparaissent. En accent, les étapes que le protocole de la
\secref{sec:protocole} déclare distinguables du bruit.}
\label{fig:ablation}
\end{figure}

La \figref{fig:ablation} vaut moins pour ses barres que pour le contraste entre ses deux
panneaux. Lues en valeurs absolues, les configurations sont indiscernables : sur dix sujets,
l'écart-type inter-sujets vaut environ $0{,}010$ de Dice, du même ordre que le plus gros gain
d'une seule étape et trois fois celui de la remontée de branche. Un lecteur qui s'arrêterait au panneau (a) conclurait, à tort, qu'aucune
étape ne fait rien. Le panneau (b) montre pourquoi c'est faux : le même sujet passant dans
toutes les configurations, la variabilité inter-sujets disparaît de la différence, et
l'intervalle de $+0{,}0122$ pour l'auto-contexte exclut zéro très largement.

C'est ce qui justifie que toutes nos comparaisons soient appariées. Un cas mérite d'être
signalé plutôt que caché : pour le palier
2 contre le palier 1, l'intervalle de confiance de Student exclut zéro alors que le test de
Wilcoxon déclaré ne conclut pas ($p = 0{,}064$ brut, $0{,}322$ après Holm). Les deux outils
divergent sur dix sujets. C'est le test déclaré qui tranche, et la figure le signale.

## Budget de frugalité

Le modèle entier tient dans **2,5 kilo-octets sur disque** pour la configuration finale, et le
temps d'inférence est de l'ordre de la seconde par volume. L'extraction des descripteurs
domine largement le coût, et à l'intérieur de l'extraction c'est le bloc gaussien puis le bloc
morphologique qui dominent. Notre frugalité est paramétrique et mémorielle bien plus que
calculatoire : nous ne prétendons pas être rapides, nous prétendons ne rien mémoriser.

Les mesures détaillées sont dans `report/assets/frugality.md`. **Attention à ne pas les lire
en travers** : elles ont été produites sur deux machines différentes, ce que l'asset signale
ligne par ligne. Seules les mesures issues de la même machine se comparent en secondes.

**Le résultat sur la quantification à 64 niveaux est négatif, et nous le corrigeons ici.** Nous
avions présenté la réduction à 64 niveaux comme un levier de frugalité. Mesurée sur une seule
et même machine pour les deux variantes, elle n'économise rien et coûte même du temps : 87,8 s
d'extraction par sujet contre 83,1 s à 256 niveaux, pour la même empreinte mémoire du bloc
morphologique, 192 Mo, et la même taille de modèle, 3,9 ko. Côté Dice elle perd $0{,}0005$,
neuf sujets sur dix dégradés, mais $p = 0{,}068$ après Holm : notre propre règle ne la déclare
pas distinguable du bruit. Un levier qui ne fait rien gagner en mémoire, coûte du temps et ne
gagne rien en Dice n'est pas un levier. Nous ne le prenons pas.

## Le meilleur et le pire sujet

\begin{figure}[t]
\centering
\includegraphics[width=\linewidth]{report/assets/fig06_qualitative.pdf}
\caption{Sujet le mieux et le moins bien segmentés du leave-one-out, avec leur carte d'erreur.
La coupe est choisie par la même règle pour les deux — celle qui contient le plus de voxels du
masque — de façon qu'aucun des deux ne soit montré sous un jour choisi. La carte d'erreur est
colorée par le tissu de la vérité terrain, donc par ce que la prédiction a manqué.}
\label{fig:qualitatif}
\end{figure}

La \figref{fig:qualitatif} montre les deux extrêmes. Le sujet 8 obtient $0{,}8506$, le sujet 2
$0{,}8215$ : l'écart entre le meilleur et le pire vaut $0{,}029$ de Dice, soit plus du double du
gain qu'apporte l'auto-contexte. **La variabilité entre sujets domine donc largement la
différence entre nos configurations**, ce qui est la justification empirique de tout le
protocole apparié de la \secref{sec:protocole}.

Le pire cas mérite d'être regardé plutôt qu'écarté. Sur le sujet 2, l'erreur ne se concentre pas
dans une région particulière : elle est distribuée le long de toute l'interface entre substance
grise et substance blanche, en un liseré d'un à deux voxels. Ce n'est pas un échec de
localisation, c'est un flou de frontière — exactement ce que la phase isointense prédit, et
exactement ce que le Dice pénalise le plus sur des structures aussi minces que le ruban
cortical. Le tissu le plus touché est la substance blanche, à $0{,}764$ contre $0{,}796$ pour le
meilleur sujet ; le LCR, dont la frontière est nettement plus contrastée, reste à $0{,}886$.

Nous ne voyons dans son T1 ni artefact ni mouvement, et nous n'avons pas d'explication
assurée à son rang. Avec dix sujets, un dernier à trois centièmes du premier n'en appelle pas.

# Discussion {#sec:discussion}

**Ce qui marche, et pourquoi.** Le fil conducteur de tous nos gains est le même : l'information
qui manque au voxel isolé est non locale. Le bloc morphologique, la remontée de branche vers
les ancêtres, et l'auto-contexte gagnent tous les trois, chacun sur dix sujets sur dix ; les
raffinements locaux ne gagnent rien. C'est la prédiction directe de la \figref{fig:isointense}
de l'introduction : à six mois, l'intensité d'un point ne sépare pas les tissus, et un
voisinage de quelques millimètres non plus.

**Le résultat négatif sur l'auto-dualité.** Nous attendions de l'arbre des formes qu'il fasse
mieux que la paire max-tree / min-tree, puisqu'il produit la même information dans une
structure unique. Il divise effectivement par deux les colonnes du bloc morphologique, 52 contre 104, ce qui
ramène le vecteur entier de 187 colonnes à 135 : exactement ce que la théorie prédit. Mais le Dice ne bouge pas
de façon distinguable : $-0{,}0002$ contre le palier 0, quatre sujets améliorés sur dix,
$p = 0{,}625$. Contre le palier 1, l'écart de $-0{,}0037$ ne franchit pas non plus notre seuil.

Nous n'avons pas d'explication certaine et nous préférons le dire. L'hypothèse que nous
trouvons la plus probable est que le classifieur linéaire ne tire aucun bénéfice de la
compacité : deux colonnes redondantes lui coûtent deux poids, pas de la performance, et la
régularisation absorbe la redondance. Le gain de l'auto-dualité serait alors réel mais
paramétrique — moins de colonnes pour le même Dice, donc un meilleur point sur le front — et
non qualitatif. Le \tabref{tab:ablation} est compatible avec cette lecture : le palier 2 fait
aussi bien que le palier 1 avec 408 paramètres au lieu de 564.

**Le résultat négatif sur le post-traitement, et l'erreur d'anatomie.** La contrainte
topologique dégrade systématiquement, et nous savons pourquoi : nous avions posé que le ruban
cortical s'interpose partout entre substance blanche et LCR, ce qui est vrai en surface et
faux aux ventricules. C'est une erreur de notre part, pas un défaut de la méthode, et elle
suggère sa propre correction : restreindre la contrainte au LCR sous-arachnoïdien, en
excluant les composantes ventriculaires. Nous ne l'avons pas fait faute de temps, et nous ne
revendiquons donc rien sur ce point.

Le cas du lissage est moins net. Il dégrade le Dice de $0{,}0031$, non distinguable du bruit,
mais il donne la meilleure ASD de toutes les configurations : il rapproche les surfaces tout en
dégradant le recouvrement volumique. Notre hypothèse, que nous n'avons pas testée, est qu'il
érode les structures les plus fines, sulci et frontières corticales.

**Le compromis de la sélection de colonnes.** Passer à 40 colonnes coûte $-0{,}0240$ de Dice et
divise le décompte par 2,8. Nous ne tranchons pas : c'est précisément ce qu'un front de Pareto
sert à ne pas trancher à la place du lecteur. Nous signalons seulement que le décompte correct
inclut les 40 indices retenus, sans quoi la sélection paraîtrait deux fois plus rentable
qu'elle ne l'est.

**Limites.** Dix sujets annotés, et une famille de quatorze comparaisons : après correction de
Holm, une p-valeur brute de $0{,}064$ devient $0{,}322$, et l'écart de $-0{,}0037$ de
l'auto-dualité reste indécidable alors que neuf sujets sur dix vont dans le même sens. Ce n'est
pas la taille d'un écart qui nous limite — nous déclarons $-0{,}0011$ — c'est le nombre de
sujets.
Aucun jeu de test externe, aucune soumission au serveur du challenge, donc **aucun de nos
chiffres n'est directement comparable aux scores publiés** — les pourcentages de la
\secref{sec:resultats} se lisent en ordre de grandeur. Les hyperparamètres des blocs sont
fixés a priori et non validés dans le pli ; ils ne sont pas ajustés sur les données, mais un
jury peut objecter qu'ils incorporent une connaissance du domaine acquise ailleurs. Enfin, la
quantification linéaire du bloc morphologique nous fait perdre l'invariance au contraste :
seule l'invariance affine subsiste, et nous l'avons dit en \secref{sec:tos} plutôt que de
revendiquer une propriété que nous n'avons plus.

**Pistes.** Trois nous paraissent valoir le coup, dans cet ordre. Restreindre la contrainte
topologique à la surface corticale, puisque l'échec est compris. Empiler un troisième étage
d'auto-contexte, puisque le deuxième gagne autant que les blocs de symétrie et de contexte
réunis. Et calculer l'arbre des formes conjointement sur T1 et T2 plutôt que modalité par
modalité, pour donner au bloc morphologique la lecture croisée dont le bloc A tire son gain.

# Conclusion

Sur la segmentation en trois tissus de cerveaux de nourrissons en phase isointense, une
régression logistique lisant des descripteurs géométriques et hiérarchiques calculés à la
volée atteint un Dice moyen de $0{,}8399$ avec 939 paramètres appris, et de $0{,}8036$ avec
163 — deux configurations de la même tranche, $10^2$. Rapporté à la méthode classée première du
challenge iSeg-2017, qui est en $10^6$, cela représente environ **90 \% de son Dice quatre
tranches d'ordre de grandeur plus bas** — un facteur 1 651 sur le décompte. La comparaison porte sur des
sujets différents et se lit en ordre de grandeur ; nous ne la présentons pas autrement.

Ces chiffres ne disent pas que la frugalité vaut mieux. Ils disent qu'une part substantielle
de ce que des millions de poids apprennent peut être remplacée par des descripteurs non
appris, à condition qu'ils soient non locaux. Tous nos gains viennent de là. Aucun de nos
trois échecs n'en vient : l'auto-dualité ne gagne pas de Dice, la contrainte topologique
repose sur une anatomie fausse, et la quantification à 64 niveaux n'économise rien.

<!--
================================================================================
Plus aucun marqueur en attente : tous les chiffres du rapport viennent de
report/assets/, régénéré par `make report-assets` depuis results/*.json.

À REVOIR si une soumission au serveur du challenge est faite un jour : deux
passages affirment qu'il n'y en a pas eu, en § Résultats (front de Pareto) et
en § Discussion (Limites).
================================================================================
-->
