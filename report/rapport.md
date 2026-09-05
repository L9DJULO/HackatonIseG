---
title: "Segmentation frugale des IRM cérébrales de nourrissons en phase isointense"
subtitle: "Hackathon SCIA 2026 — sujet 2, challenge MICCAI iSeg-2017"
author:
  - Jules Lange
  - "Arthur Goullet de Rugy"
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
  substituons un front de Pareto, et nous rapportons trois résultats négatifs : l'auto-dualité
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
hiérarchiques calculés à la volée. Notre configuration la plus performante, celle qui ajoute
l'auto-contexte décrit en \secref{sec:classifieur}, obtient un Dice moyen de $0{,}8399$ pour
**939 paramètres appris** ; la plus frugale de notre famille en obtient $0{,}8036$ pour 163. La
méthode classée première du challenge en emploie un million et demi.

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
$0{,}214 \pm 0{,}008$ et un ratio brut soixante-sept fois supérieur au meilleur ratio
atteint par une configuration réelle, et cent dix-huit fois supérieur à celui de notre
configuration finale. Une métrique qui classe ce modèle premier n'est pas une métrique de
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
quotient. Le second est la comparaison d'ordre de grandeur. La méthode arrivée première du
challenge, un réseau densément connecté à quarante-sept couches, compte
$1{,}55 \cdot 10^{6}$ paramètres appris ; le chiffre est donné par l'article de synthèse du
challenge lui-même [@wang2019iseg]. Les autres participations ne publient pas toutes le
leur, mais les architectures que le même article décrit — VGG-16 transféré, U-Net 3D à cinq
niveaux de sous-échantillonnage, V-Net augmenté — situent l'ensemble entre $10^{6}$ et
$10^{8}$ paramètres. Cette seconde borne est une estimation d'ordre de grandeur déduite des
architectures et non un compte publié : elle est signalée comme telle partout où elle
apparaît, y compris sur le front de Pareto. Nous en avons quelques centaines, soit trois à
quatre ordres de grandeur de moins. Enfin, à l'intérieur de notre propre famille de
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

Le classifieur est une régression logistique multinomiale. À $F$ colonnes elle coûte
exactement $3(F+1)$ poids, soit 456 pour les 151 colonnes de la configuration finale. Deux
raisons à ce choix, et la seconde compte autant que la première. C'est le plus petit modèle
qui sache encore combiner linéairement des descripteurs d'échelles et d'unités différentes ;
c'est surtout un modèle dont le décompte ne se discute pas, là où un modèle à base d'arbres
obligerait à convenir d'abord de ce que coûte un nœud. La régularisation vaut $C = 1$ et le
nombre d'itérations 300, tous deux fixés a priori et jamais choisis sur les labels.
L'optimiseur en réclame 319 pour converger complètement : l'écart a été mesuré sur un pli, le
Dice est identique à la quatrième décimale et la norme des poids passe de 10,33 à 10,19.

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
donc zéro paramètre appris, et c'est ce qui le rend intéressant dans un projet dont le
critère est le nombre de paramètres. Un seuil qui aurait été ajusté sur les labels
d'entraînement, lui, devrait être compté.

**La sélection de colonnes n'est pas gratuite.** On peut ne garder que les $K$ colonnes de
plus grand poids et réajuster. Le décompte passe alors de $3(F+1)$ à $3(K+1) + K$, car les
indices retenus sont ajustés sur les sujets d'entraînement et doivent être transportés : sans
eux, on ne sait pas quelles colonnes présenter au modèle. Ils tombent donc sous la règle de
la \secref{sec:comptage} et sont comptés, un entier par colonne. À $K = 40$, cela fait 163
paramètres contre 456. Le rapport devra présenter le gain net, pas la seule réduction du
nombre de poids.

**Ce que les trois donnent, mesuré.** Les résultats complets sont en
\secref{sec:resultats} ; voici ce qu'ils disent de ces trois mécanismes, y compris quand ils
disent non.

L'auto-contexte gagne, et nettement : $0{,}8399$ contre $0{,}8276$, soit $+0{,}0122$ de Dice
sur les dix sujets, dix sujets améliorés sur dix, $p = 0{,}002$ brut et $0{,}027$ après Holm.
C'est le même ordre de gain que l'ajout de tous les blocs de descripteurs à la configuration
de référence, pour un peu plus du double de paramètres — 939 contre 456. Il améliore aussi
les deux métriques de distance, ASD et MHD, ce qui n'allait pas de soi.

La sélection à 40 colonnes coûte ce qu'elle prétend économiser, et le front de Pareto de la
\figref{fig:pareto} est là pour arbitrer : $0{,}8036$ pour 163 paramètres, soit $-0{,}0240$
de Dice contre la configuration finale, zéro sujet amélioré sur dix. C'est une dégradation
franche et systématique, mais elle achète un facteur 2,8 sur le décompte. Ce n'est donc pas
un échec : c'est le point le plus frugal de notre front, et le seul argument valable pour ou
contre est celui du compromis, pas celui du Dice seul.

**Le post-traitement, lui, ne marche pas, et l'erreur est instructive.** Le lissage et le
nettoyage des composantes coûtent $-0{,}0031$ de Dice, trois sujets améliorés sur dix, non
distinguable du bruit ; la contrainte topologique ajoutée par-dessus coûte encore
$-0{,}0011$, zéro sujet amélioré sur dix, et cette dégradation-là est parfaitement
systématique. La raison de la seconde est une erreur d'anatomie de notre part, pas un défaut
d'implémentation. Nous avons posé que le ruban cortical s'interpose partout entre substance
blanche et LCR. C'est vrai en surface. C'est faux aux ventricules, où la substance blanche
périventriculaire borde directement le LCR ventriculaire, sans matière grise entre les deux.
La contrainte force donc de la matière grise le long de toute la paroi ventriculaire, où il
n'y en a pas. Restreinte au LCR sous-arachnoïdien, elle resterait défendable ; appliquée
partout, elle est fausse, et la mesure la punit exactement là où on l'attendrait.

Quant au lissage, l'explication tient sans doute à ce que les blocs B et F fournissent déjà
un voisinage multi-échelle : la carte de probabilités est régularisée en amont, et lisser une
seconde fois érode les structures fines, sulci et frontières corticales. Il faut noter que
sur l'ASD, seule métrique où il gagne, le lissage donne la meilleure valeur de toutes les
configurations — il rapproche les surfaces tout en dégradant le recouvrement, ce qui est
cohérent avec cette lecture.

Les trois mécanismes sont couverts par la suite de tests, y compris un test d'intégration qui
fait tourner la boucle leave-one-out complète sur des sujets de synthèse, et un test de
régression sur un blocage de la contrainte topologique que seules les vraies données avaient
révélé.

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

Un jury peut être en désaccord avec cette frontière, et il doit trouver son propre chiffre
ici plutôt que d'avoir à le reconstituer. **Selon la convention inverse, où le scaler serait
compté, la configuration finale passe de 456 à 758 paramètres** : $2 \times 151$ valeurs de
plus, une moyenne et un écart-type par colonne. Les deux chiffres racontent la même histoire
à l'échelle qui nous intéresse — 758 reste trois ordres de grandeur sous le million et demi
de paramètres de la méthode classée première du challenge. La convention retenue change le
décompte de deux tiers, elle ne change pas la conclusion.

# Protocole expérimental {#sec:protocole}

**Leave-one-out.** Dix plis sur les dix sujets annotés : à chaque pli, neuf sujets entraînent
et le dixième est segmenté entièrement. Les graines sont fixées, la graine d'échantillonnage
dérive du numéro du sujet de test, et une seule commande reproduit n'importe quel résultat du
rapport, `python -m src.cli run experiments/<config>.yaml`, qui écrit un JSON dans `results/`.
Tous les chiffres du rapport sont régénérés depuis ces JSON par `make report-assets` ; aucun
n'est recopié à la main.

**Le contrôle anti-fuite.** C'est la propriété la plus critique du protocole, et elle est
vérifiée mécaniquement plutôt que par relecture. Chaque bloc de descripteurs est calculé trois
fois sur le même sujet : avec la vraie carte de labels, avec une carte permutée où les tissus
ont changé d'étiquette, et sans aucune carte, comme sur les treize sujets de test. Le test
exige que les trois sorties soient identiques bit à bit. Un bloc qui lirait la vérité terrain,
même indirectement, échouerait immédiatement. Un second test vérifie qu'aucun bloc ne garde
d'état d'un sujet à l'autre.

**Métriques.** Les trois du challenge, et toutes les trois rapportées : Dice, distance de
surface moyenne (ASD) et distance de Hausdorff modifiée (MHD, 95\textsuperscript{e}
percentile des distances de surface symétriques). Elles sont calculées par classe et par
sujet, jamais agrégées sur les voxels de plusieurs sujets, et le fond n'est jamais évalué. Le
\secref{sec:resultats} donne le Dice dans le corps du texte et les distances dans un tableau
séparé : le Dice mesure un recouvrement de volume, les distances mesurent une erreur de
frontière, et une méthode peut gagner sur l'un sans gagner sur l'autre — ce qui arrive
effectivement dans nos résultats.

**Protocole statistique.** Dix sujets, c'est peu, et un écart de quelques millièmes de Dice
peut n'être que du bruit. Le même sujet passant dans toutes les configurations, toutes les
comparaisons sont appariées. Chacune rapporte le delta moyen et son écart-type inter-sujets,
le test des rangs signés de Wilcoxon bilatéral, la taille d'effet — $d$ de Cohen apparié et
$\delta$ de Cliff, non paramétrique — et le nombre de sujets améliorés sur dix. Ce dernier
mérite sa justification : à $n = 10$ l'amplitude d'un gain est bruitée, mais sa systématicité
ne l'est pas, et un gain porté par un seul sujet n'est pas un gain. Un effet est déclaré
distinguable du bruit si la p-valeur ajustée est inférieure à 0,05 **et** si au moins huit
sujets sur dix vont dans le même sens ; le critère est symétrique, une dégradation
systématique reste un résultat.

Les quatorze comparaisons sont déclarées à l'avance — chacune au moment où la configuration
qu'elle concerne a été figée dans `experiments/`, avant son exécution — et corrigées de la
multiplicité par la méthode de Holm appliquée à la famille entière. Corriger sur un
sous-ensemble donnerait une correction plus permissive que la vérité ; c'est l'erreur à ne pas
commettre quand on ajoute une configuration en cours de route. Le verdict est rendu sur la
p-valeur ajustée, jamais sur la brute. Avec $n = 10$ la plus petite p-valeur atteignable vaut
0,002 : sur une famille de quatorze elle devient 0,027, et tous les gains que nous
revendiquons la franchissent. La correction ne nous coûte donc aucun résultat — raison de plus
pour l'appliquer plutôt que d'argumenter qu'elle serait facultative.

# Résultats {#sec:resultats}

Toutes les valeurs de cette section viennent de `report/assets/`, régénéré depuis les JSON de
`results/` par `make report-assets`. Aucune n'est écrite à la main.

## Ablation

Le \tabref{tab:ablation} donne les douze configurations. Trois lectures s'en dégagent, et la
troisième est celle qui compte.

D'abord, **le contexte non local paye et la description locale plafonne**. Passer de A+B+C au
bloc morphologique gagne $+0{,}0102$ de Dice sur dix sujets sur dix ; la remontée de branche
en ajoute $+0{,}0035$, également sur dix sujets sur dix. Les deux survivent à la correction de
Holm. À l'inverse, les raffinements purement locaux — filtres de grain, quantification par
rang — ne produisent aucun effet distinguable. C'est exactement ce que la phase isointense
laissait attendre : ce qui manque au voxel n'est pas dans son voisinage immédiat.

Ensuite, **l'auto-contexte prolonge le même mouvement**, et c'est cohérent : il ajoute du
contexte non local, non plus sur les intensités mais sur les décisions. Il porte le Dice à
$0{,}8399$, gagne sur les dix sujets, et améliore les trois métriques à la fois — seul point
du tableau à obtenir simultanément le meilleur Dice, le meilleur ASD et le meilleur MHD.

Enfin, **deux mécanismes échouent, et nous les gardons dans le tableau**. Le post-traitement
dégrade ; l'arbre des formes n'apporte rien contre la paire max-tree / min-tree. Les
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

Ces pourcentages se lisent en ordre de grandeur et pas autrement, pour la raison écrite sur la
figure et déjà donnée en \secref{sec:probleme} : les deux nuages ne sont pas évalués sur les
mêmes sujets. Nous n'avons pas soumis au serveur du challenge, donc nous ne pouvons pas
prétendre à une comparaison exacte, et nous ne le prétendons pas.

## Ce que valent les intervalles, et ce que valent les tests

\begin{figure}[t]
\centering
\includegraphics[width=\linewidth]{report/assets/fig05_ablation.pdf}
\caption{Ablation en barres. (a)~Dice absolu de chaque configuration, intervalle de confiance
à 95 \% de la moyenne sur les dix sujets : tous les intervalles se chevauchent. (b)~Delta
apparié contre l'étape précédente : la variabilité inter-sujets s'annule dans la différence et
des effets nets apparaissent. En accent, les étapes que le protocole de la
\secref{sec:protocole} déclare distinguables du bruit.}
\label{fig:ablation}
\end{figure}

La \figref{fig:ablation} vaut moins pour ses barres que pour le contraste entre ses deux
panneaux. Lues en valeurs absolues, les configurations sont indiscernables : sur dix sujets,
l'écart-type inter-sujets vaut environ $0{,}011$ de Dice, soit trois fois le plus gros effet
que nous mesurons. Un lecteur qui s'arrêterait au panneau (a) conclurait, à tort, qu'aucune
étape ne fait rien. Le panneau (b) montre pourquoi c'est faux : le même sujet passant dans
toutes les configurations, la variabilité inter-sujets disparaît de la différence, et
l'intervalle de $+0{,}0122$ pour l'auto-contexte exclut zéro très largement.

C'est le seul argument statistique de ce rapport, et il justifie à lui seul que toutes nos
comparaisons soient appariées. Un cas mérite d'être signalé plutôt que caché : pour le palier
2 contre le palier 1, l'intervalle de confiance de Student exclut zéro alors que le test de
Wilcoxon déclaré ne conclut pas ($p = 0{,}064$ brut, $0{,}258$ après Holm). Les deux outils
divergent sur dix sujets. C'est le test déclaré qui tranche, et la figure le signale.

## Budget de frugalité

Le modèle entier tient dans **2,5 kilo-octets sur disque** pour la configuration finale, et le
temps d'inférence est de l'ordre de la seconde par volume. L'extraction des descripteurs
domine largement le coût, et à l'intérieur de l'extraction c'est le bloc gaussien puis le bloc
morphologique qui dominent. La frugalité de cette approche est donc paramétrique et mémorielle
bien plus que calculatoire : nous ne prétendons pas être rapides, nous prétendons ne rien
mémoriser.

Les mesures détaillées sont dans `report/assets/frugality.md`. **Attention à ne pas les lire
en travers** : elles ont été produites sur deux machines différentes, ce que l'asset signale
ligne par ligne. Seules les mesures issues de la même machine se comparent en secondes.

**Le résultat sur la quantification à 64 niveaux est négatif, et nous le corrigeons ici.** Nous
avions présenté la réduction à 64 niveaux comme un levier de frugalité. La mesure, faite sur
une seule et même machine pour les deux variantes, ne montre aucune économie : 79,9 s contre
80,2 s d'extraction par sujet, même empreinte mémoire du bloc morphologique à 192 Mo, même
taille de modèle à 3,9 ko. Et elle coûte $-0{,}0005$ de Dice, dégradation faible mais
systématique — neuf sujets sur dix, $p = 0{,}049$ après Holm. Une option qui coûte un peu et ne
rapporte rien de mesurable n'est pas un levier de frugalité : c'est une option à ne pas
prendre, et nous ne la prenons pas.

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

Nous ne voyons dans le T1 du sujet 2 rien qui le distingue franchement des autres, ni artefact
ni mouvement visible, et nous n'avons donc pas d'explication assurée à son rang. Avec dix
sujets, un dernier de classement à trois centièmes du premier n'appelle de toute façon pas
d'explication : c'est l'amplitude normale de la variabilité inter-sujets que la
\figref{fig:ablation} montre par ailleurs.

# Discussion {#sec:discussion}

**Ce qui marche, et pourquoi.** Le fil conducteur de tous nos gains est le même : l'information
qui manque au voxel isolé est non locale. Le bloc morphologique, la remontée de branche vers
les ancêtres, et l'auto-contexte gagnent tous les trois, chacun sur dix sujets sur dix ; les
raffinements locaux ne gagnent rien. C'est la prédiction directe de la \figref{fig:isointense}
de l'introduction : à six mois, l'intensité d'un point ne sépare pas les tissus, et un
voisinage de quelques millimètres non plus.

**Le résultat négatif sur l'auto-dualité.** Nous attendions de l'arbre des formes qu'il fasse
mieux que la paire max-tree / min-tree, puisqu'il produit la même information dans une
structure unique. Il divise effectivement par deux le nombre de colonnes à attributs
identiques — 135 contre 187 — exactement comme la théorie le prédit. Mais le Dice ne bouge pas
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
mais il donne la meilleure ASD de toutes les configurations. Autrement dit il rapproche les
surfaces tout en dégradant le recouvrement volumique — ce qui est cohérent avec l'idée qu'il
érode les structures fines, sulci et frontières corticales, déjà régularisées en amont par les
blocs gaussien et contexte.

**Le compromis de la sélection de colonnes.** Passer à 40 colonnes coûte $-0{,}0240$ de Dice et
divise le décompte par 2,8. Nous ne tranchons pas : c'est précisément ce qu'un front de Pareto
sert à ne pas trancher à la place du lecteur. Nous signalons seulement que le décompte correct
inclut les 40 indices retenus, sans quoi la sélection paraîtrait deux fois plus rentable
qu'elle ne l'est.

**Limites.** Elles sont sévères et nous les énonçons sans atténuation. Dix sujets annotés
seulement : tout écart inférieur à $0{,}005$ de Dice est hors de portée de notre protocole.
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
d'auto-contexte, puisque le deuxième gagne autant que tous les blocs de descripteurs réunis.
Et calculer l'arbre des formes conjointement sur T1 et T2 plutôt que modalité par modalité, ce
qui rendrait au bloc morphologique le comportement croisé qui fait toute la valeur du bloc A.

# Conclusion

Sur la segmentation en trois tissus de cerveaux de nourrissons en phase isointense, une
régression logistique lisant des descripteurs géométriques et hiérarchiques calculés à la
volée atteint un Dice moyen de $0{,}8399$ avec 939 paramètres appris, et de $0{,}8036$ avec
163. Rapporté à la méthode classée première du challenge iSeg-2017, cela représente environ
90 % de son Dice pour trois ordres de grandeur de paramètres en moins — comparaison d'ordre de
grandeur, sur des sujets différents, et nous ne la présentons pas autrement.

Ce que ces chiffres soutiennent n'est pas que la frugalité vaut mieux, mais qu'une part
substantielle de ce que des millions de poids apprennent peut être remplacée par des
descripteurs non appris, à condition qu'ils soient non locaux. Nos gains viennent tous de là,
et nos échecs — l'auto-dualité sans gain de Dice, la contrainte topologique fondée sur une
anatomie fausse, la quantification qui ne fait économiser rien — viennent tous d'ailleurs.

<!--
================================================================================
Plus aucun marqueur en attente : tous les chiffres du rapport viennent de
report/assets/, régénéré par `make report-assets` depuis results/*.json.

À REVOIR si une soumission au serveur du challenge est faite un jour : deux
passages affirment qu'il n'y en a pas eu, en § Résultats (front de Pareto) et
en § Discussion (Limites).
================================================================================
-->
