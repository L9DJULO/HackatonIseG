"""Passe éditoriale finale : conserver les figures et les tableaux déjà vérifiés."""
from pathlib import Path
import re

root = Path(__file__).resolve().parents[1]
p = root / 'report/rapport.md'
old = p.read_text(encoding='utf-8')
figs = re.findall(r'\\begin\{figure\}.*?\\end\{figure\}', old, re.S)
def figure(index, caption, width='0.94'):
    f = figs[index]
    path = re.search(r'\\includegraphics\[.*?\]\{(.*?)\}', f).group(1)
    label = re.search(r'\\label\{(.*?)\}', f).group(1)
    return '\n'.join([r'\begin{figure}[htbp]', r'\centering',
        rf'\includegraphics[width={width}\linewidth]{{{path}}}',
        rf'\caption{{{caption}}}', rf'\label{{{label}}}', r'\end{figure}'])

header = old.split('---', 2)[1]
header = re.sub(r'abstract: \|.*?\nlang:', '''abstract: |
  Pendant ce hackathon, nous avons étudié la segmentation des IRM de nourrissons
  avec un modèle qui apprend peu de paramètres. Notre solution combine des descripteurs
  d'intensité, de position et de morphologie avec une régression logistique à deux étages.
  Elle obtient un Dice moyen de 0,8399 en leave-one-out sur dix sujets annotés et de
  0,8445 sur les treize sujets du test officiel iSeg-2017, pour 939 paramètres appris.
  L'ajout de contexte améliore nos résultats internes. En revanche, l'auto-dualité
  n'apporte pas de gain de Dice démontré et le post-traitement testé n'est pas retenu.
  Le modèle reste nettement moins précis que les références publiées, notamment sur
  les distances de surface. Ce travail montre un compromis entre qualité de segmentation
  et nombre de paramètres, avec les limites d'une expérimentation de hackathon.
lang:''', header, flags=re.S)

body = r'''
# Introduction

Le but du projet est de segmenter une IRM cérébrale en trois tissus : liquide
céphalo-rachidien (LCR), substance grise (SG) et substance blanche (SB). Nous travaillons
sur le challenge iSeg-2017, consacré aux nourrissons de six mois [@wang2019iseg]. À cet
âge, la SG et la SB ont des intensités proches dans les images T1 et T2. Une simple
séparation par seuils devient donc difficile.

Nous avons commencé par regarder les données. Sur les dix sujets annotés, le recouvrement
des histogrammes SG/SB vaut $0{,}701 \pm 0{,}048$ en T1 et $0{,}867 \pm 0{,}041$ en T2.
Ces valeurs décrivent une difficulté de séparation par intensité ; elles ne constituent
pas une limite générale de performance pour tous les classifieurs.

@@FIG0@@

La contrainte du hackathon nous a conduits à chercher une solution simple à entraîner et
économe en paramètres. Nous calculons des descripteurs sur chaque image, puis nous les
donnons à une régression logistique. L'idée est d'apporter au classifieur des informations
sur le voisinage et la forme des régions, au lieu de lui demander de tout apprendre.

La configuration soumise contient **939 paramètres appris**. Son Dice moyen officiel est
de **0,8445** sur les treize sujets de test. La référence MSL\_SKKU retenue pour la comparaison
atteint 0,9283, avec un réseau annoncé à 1,55 million de paramètres. Notre score représente
91,0 % de ce Dice. Ce pourcentage situe l'écart ; il ne signifie pas que les segmentations
ont une qualité équivalente.

# Données et choix de la métrique {#sec:probleme}

Le jeu fourni comporte dix sujets annotés et treize sujets de test dont les annotations
ne sont pas publiques. Nous utilisons les volumes T1 et T2 prétraités, sur une grille de
$144 \times 192 \times 256$ voxels de 1 mm. Les scores internes et officiels sont séparés
dans tout le rapport : le leave-one-out sert à comparer nos variantes ; le serveur sert
à évaluer la configuration retenue sur les sujets de test.

Le Dice mesure le recouvrement entre une prédiction $P$ et la référence $G$ :
$\mathrm{Dice}=2|P\cap G|/(|P|+|G|)$. Nous le calculons par tissu et par sujet, puis
nous faisons la moyenne des trois tissus. Le fond est exclu. Nous rapportons aussi les
distances de surface ASD et MHD, car un bon recouvrement ne garantit pas des contours précis.

## Pourquoi ne pas sélectionner avec Dice / paramètres ?

Sur nos essais, ce ratio favorise trop les petits modèles. Le contre-exemple le plus
simple est un classifieur qui prédit partout le tissu majoritaire de l'entraînement.
Il mémorise un seul indice de classe, segmente mal, mais gagne largement selon ce ratio.

| configuration | paramètres | Dice interne | Dice / paramètres |
|:-----------------------------|----------:|-------------:|------------------:|
| tissu majoritaire partout | 1 | 0,2139 | 0,2139 |
| sélection de 40 colonnes | 163 | 0,8036 | $4{,}93\cdot10^{-3}$ |
| A+B+C, sans morphologie | 252 | 0,8055 | $3{,}20\cdot10^{-3}$ |
| tous les blocs | 456 | 0,8276 | $1{,}81\cdot10^{-3}$ |
| tous les blocs + auto-contexte | 939 | 0,8399 | $8{,}94\cdot10^{-4}$ |

: Extrait des essais en leave-one-out. La sélection à 40 colonnes a le meilleur ratio
parmi les modèles réels, mais le moins bon Dice. \label{tab:ratio}

Nous utilisons donc un **front de Pareto** : une configuration est intéressante si aucune
autre n'obtient un Dice au moins aussi élevé avec moins de paramètres, ou un meilleur Dice
avec autant de paramètres. Cela laisse visible le compromis au lieu de le réduire à un
quotient. Pour les références publiées, nous comparons aussi les ordres de grandeur.
Cette lecture repose sur un comptage explicite, décrit en \secref{sec:comptage}.

# Méthode {#sec:methode}

## Principe

Chaque voxel du masque cérébral est décrit par une ligne de valeurs. Les descripteurs sont
recalculés sur le sujet à segmenter : ils n'utilisent ni ses labels ni ceux d'un autre
sujet. Les coefficients de la régression logistique sont, eux, appris sur l'entraînement.
Le calcul des descripteurs ne coûte donc aucun paramètre appris, mais il prend du temps
et de la mémoire. Nous distinguons ces deux coûts.

@@FIG1@@

## Les six blocs de descripteurs

**A — Intensités, 6 colonnes.** Les valeurs T1 et T2 normalisées, leurs rangs percentiles,
leur différence et un ratio normalisé. Ces informations gardent le contraste disponible
dans les images. Toutes les normalisations sont calculées dans le masque du sujet.

**B — Voisinage gaussien, 68 colonnes.** Des lissages, gradients, laplaciens et descripteurs
de courbure décrivent le signal à cinq échelles : $0{,}5$, 1, 2, 4 et 8 mm.
Les différences entre échelles complètent ce bloc. Les calculs au bord tiennent compte
du masque pour limiter l'effet du fond de l'image.

**C — Position, 9 colonnes.** Coordonnées dans le masque, distance à son bord, distance
au plan médian et coordonnées autour du centre du cerveau. Le repère est estimé sur le
sujet courant. Nous n'utilisons pas d'atlas appris sur la population.

**D — Morphologie, 52 colonnes.** Les régions de l'image sont organisées en arbre.
Nous lisons leurs attributs à plusieurs tailles, comme décrit juste après.

**E — Symétrie, 4 colonnes.** Pour chaque modalité, nous utilisons l'intensité au point
miroir par rapport au plan médian et sa différence avec l'intensité du voxel. Cela fournit
un repère supplémentaire, sans imposer que le cerveau soit parfaitement symétrique.

**F — Contexte local, 12 colonnes.** Moyennes et écarts-types des rangs d'intensité dans
des voisinages de rayon 1, 2 et 4 voxels. Ce bloc décrit les images ; l'auto-contexte décrit
les probabilités prédites par un premier classifieur.

## Arbre des formes et remontée de branche {#sec:tos}

C'est la partie morphologique que nous avons le plus explorée. Un max-tree organise les
régions claires obtenues par seuillage ; un min-tree fait de même pour les régions sombres
[@salembier1998antiextensive]. Nous les avons utilisés comme première solution.

L'arbre des formes rassemble les régions claires et sombres dans une seule hiérarchie
d'inclusion, après remplissage de leurs trous [@monasse2000fast]. Une petite région peut
ainsi être rattachée à une région plus grande qui l'entoure. Nous utilisons la bibliothèque
Higra [@perret2019higra], avec son calcul de l'arbre en trois dimensions ; les algorithmes
associés sont décrits notamment par Géraud et al. [@geraud2013quasilinear].

@@FIG2@@

Pour chaque voxel, nous partons du plus petit nœud qui le contient. Nous lisons six
attributs : aire relative, profondeur, contraste avec le parent, dynamique, sphéricité
et extension. Ces mesures s'inscrivent dans l'utilisation des attributs de régions en
morphologie [@breen1996attribute]. Elles décrivent la taille, la forme et le contraste
des régions, sans entraînement.

Nous remontons ensuite la branche jusqu'au premier ancêtre qui atteint chacun des seuils
d'aire : $100$, $1\,000$, $10\,000$ et $100\,000$ voxels. À chaque seuil, cinq attributs
sont conservés. Le voxel reçoit ainsi des informations sur de plus grandes régions que
son voisinage immédiat. Avec les deux modalités, cela donne
$2\times(6+4\times5)=52$ colonnes. Ces seuils sont fixés dans la configuration.

L'arbre des formes est auto-dual : il traite de façon symétrique les régions claires et
sombres. Cela réduit le nombre de colonnes par rapport à deux arbres séparés. **Nous
n'observons toutefois pas de gain de Dice démontré grâce à cette propriété.** C'est un
résultat négatif du projet, détaillé dans la discussion.

Avant de construire l'arbre, les intensités sont quantifiées sur 256 niveaux entre les
percentiles 1 et 99 du sujet. Cette étape simplifie le calcul, mais ne conserve pas une
invariance générale aux changements de contraste. Nous ne revendiquons pas cette
invariance pour notre chaîne de traitement. La variante de quantification par rang a
également été testée, sans amélioration du Dice.

## Classifieur, auto-contexte et variantes {#sec:classifieur}

Le classifieur de base est une régression logistique multinomiale. Il combine les colonnes
pour attribuer une probabilité à chaque tissu. Nous avons conservé la régularisation
$C=1$ et une limite de 300 itérations, sans recherche étendue d'hyperparamètres.

**Auto-contexte.** Un premier classifieur produit les probabilités des trois tissus.
Nous les lissons aux échelles 1, 2 et 4 mm, puis ajoutons ces neuf colonnes aux descripteurs
d'origine. Un second classifieur peut ainsi tenir compte des décisions prises autour du
voxel [@tu2010autocontext].

Pendant l'entraînement, il faut éviter de fournir au second étage des prédictions trop
favorables parce que le premier aurait déjà vu les sujets. Nous produisons donc ces
cartes par une validation croisée interne à trois plis, uniquement sur les sujets
d'entraînement. En leave-one-out externe, cette boucle ne porte que sur les neuf sujets
restants. Le dixième n'intervient dans aucune étape d'apprentissage. Le premier étage
final est ensuite réentraîné sur tout l'entraînement ; seuls les deux étages finaux sont
conservés pour la prédiction.

**Post-traitement.** Nous avons essayé un lissage des probabilités à 1 mm, le nettoyage
des composantes de moins de 30 mm³, puis une règle interdisant les contacts directs entre
SB et LCR. Cette dernière hypothèse est trop forte, notamment au voisinage des ventricules.
Les résultats ne justifient pas de conserver ce post-traitement dans la soumission.
Le lissage et le nettoyage ont été mesurés ensemble ; leur contribution individuelle
n'a pas été isolée. L'effet supplémentaire de la contrainte de contact a été mesuré séparément.

**Sélection de colonnes.** Une autre variante ne conserve que les 40 colonnes de plus
grand poids, choisies dans l'entraînement de chaque pli, puis réajuste le classifieur.
Elle réduit la taille du modèle, au prix d'une baisse du Dice.

## Comptage des paramètres {#sec:comptage}

\begin{encadre}{Convention retenue}
Nous comptons toute quantité ajustée sur l'entraînement et conservée pour prédire un
nouveau sujet : poids, biais et indices de colonnes sélectionnées. Les statistiques
recalculées sur le sujet courant et les hyperparamètres fixés dans la configuration
ne sont pas des paramètres appris.
\end{encadre}

Pour $F=151$ colonnes et trois classes, le modèle de base contient exactement
$3(F+1)=456$ paramètres. Avec l'auto-contexte, les deux étages contiennent
$3(F+1)+3(F+10)=939$ paramètres. Pour la sélection à 40 colonnes, nous comptons
$3(40+1)+40=163$, indices compris. Le gain par rapport aux 456 paramètres est donc
de 293 paramètres, soit 64,3 %.

La standardisation est faite par sujet. Selon une convention alternative qui compterait
aussi ses moyennes et écarts-types, le modèle de base aurait
$456+2\times151=758$ valeurs. Pour la chaîne soumise, qui réutilise les mêmes colonnes
standardisées aux deux étages, ce total serait $939+2\times151=1\,241$.
Ces comptes sont exacts selon les conventions indiquées. Notre comparaison d'ordre de
grandeur ne doit pas masquer cette définition.

# Protocole expérimental {#sec:protocole}

**Évaluation interne.** Nous réalisons dix plis de leave-one-out : entraînement sur neuf
sujets, prédiction du sujet restant. L'échantillonnage est reproductible et la sélection
de colonnes reste dans l'entraînement. Les configurations sont comparées sur les mêmes
sujets, avec des deltas appariés.

**Contrôles.** Les tests vérifient notamment que les descripteurs ne changent pas si les
labels sont remplacés ou retirés, et qu'ils ne gardent pas d'état appris entre sujets.
Ces contrôles ciblent des risques précis de fuite ; ils ne prouvent pas à eux seuls
l'absence de toute erreur dans le protocole.

**Statistiques.** Les quatorze comparaisons du script de résultats utilisent un test de
Wilcoxon apparié, avec correction de Holm. Nous retenons un effet si la p-valeur corrigée
est inférieure à 0,05 et si au moins huit sujets sur dix évoluent dans le même sens.
Ce sont des analyses exploratoires sur un petit échantillon, pas une validation sur une
grande population. Les détails sont conservés dans `report/assets/stats.md`.

**Test officiel.** Le fichier `results/submission.json` indique un entraînement final sur
**les dix sujets annotés**, puis la prédiction des sujets 11 à 23 avec l'auto-contexte.
Le classeur du serveur est conservé dans `results/`. Ses moyennes et écarts-types sont
recalculés par le script de génération et vérifiés contre ceux du classeur.

**Distances.** Le code interne utilise une ASD symétrique et un 95\textsuperscript{e}
percentile des distances de surface, nommé MHD dans nos JSON. L'article du challenge
décrit aussi une distance HD95 [@wang2019iseg]. Nous n'avons cependant pas vérifié
l'équivalence exacte entre l'implémentation locale et celle du serveur. Les comparaisons
avec les publications utilisent donc uniquement nos distances officielles.

# Résultats {#sec:resultats}

## Comparaison des variantes en leave-one-out

@@ABLATION@@

Le premier bloc morphologique apporte $+0{,}0102$ de Dice moyen par rapport à A+B+C.
La remontée de branche ajoute $+0{,}0035$ à cette variante. Dans les deux cas, les dix
sujets progressent et les tests restent significatifs après correction de Holm.

L'auto-contexte donne notre meilleur Dice interne, **0,8399**, contre **0,8276** pour le
modèle de base avec tous les blocs. Le gain calculé sur les valeurs non arrondies est
$+0{,}0122$, avec dix sujets améliorés. La sélection à 40 colonnes descend à 0,8036.

Le lissage et le nettoyage font perdre $0{,}0031$ de Dice en moyenne. La contrainte
topologique ajoute une baisse de $0{,}0011$. Seule cette baisse supplémentaire est
significative selon notre règle corrigée. Les filtres de grain et la quantification par
rang n'apportent pas de gain démontré.

@@FIG4@@

## Résultats sur les treize sujets du test officiel

@@TEST@@

Le Dice moyen officiel est **0,8445**. Le meilleur sujet de test est le 13, à 0,8600 ;
le moins bon est le 20, à 0,8226. L'écart-type du Dice moyen entre sujets vaut 0,0113.

Par rapport au leave-one-out de l'auto-contexte, les écarts calculés avant arrondi sont
$+0{,}0079$ pour le LCR, $+0{,}0038$ pour la SG et $+0{,}0022$ pour la SB, soit
$+0{,}0047$ en moyenne. Le résultat officiel est donc proche, et légèrement supérieur,
à notre estimation interne. Les sujets diffèrent et le modèle final utilise un sujet
d'entraînement de plus. **Cet écart ne prouve ni l'absence de fuite ni le caractère
conservateur du protocole.** Il constitue un contrôle supplémentaire sur des données
dont nous n'avons pas les annotations.

## Comparaison aux méthodes publiées et front de Pareto

@@FIG3@@

Les scores de MSL\_SKKU et HyperDenseNet sont ceux du second tour rapportés dans le
tableau 5 de Dolz et al. [@dolz2019hyperdensenet]. Ils portent sur le test iSeg-2017.
Ce sont des références historiques, pas une affirmation sur le classement actuel.
MSL\_SKKU obtient un Dice moyen de 0,9283, HyperDenseNet de 0,9257, contre notre 0,8445.

Notre score atteint **91,0 % du Dice de MSL\_SKKU** : 93,9 % pour le LCR, 90,7 % pour la
SG et 88,1 % pour la SB. L'écart reste net, surtout pour la substance blanche.
Le compte publié du réseau MSL\_SKKU est de 1,55 million de paramètres [@wang2019iseg],
soit un facteur d'environ 1 651 par rapport à nos 939 paramètres. Les auteurs décrivent
aussi un vote entre modèles : ce compte de réseau n'est pas un décompte vérifié de
l'ensemble complet utilisé pour la prédiction. HyperDenseNet annonce 10 349 450 paramètres
dans son tableau 4, soit environ 11 022 fois notre compte. Nous reprenons les comptes
publiés, sans estimer celui d'autres méthodes. Ces facteurs correspondent à environ
trois et quatre ordres de grandeur.

La comparaison des distances est moins favorable :

| méthode | MHD LCR | MHD SG | MHD SB | ASD LCR | ASD SG | ASD SB |
|:----------------|-------:|------:|------:|--------:|-------:|-------:|
| notre soumission | 10,772 | 8,300 | 12,765 | 0,297 | 0,614 | 0,798 |
| MSL\_SKKU | 9,112 | 5,999 | 6,618 | 0,116 | 0,321 | 0,375 |
| HyperDenseNet | 9,421 | 5,752 | 6,660 | 0,120 | 0,329 | 0,382 |

: Distances officielles en mm ; plus bas est meilleur. Références : tableau 5 de
Dolz et al., second tour. Notre ligne est recalculée depuis le classeur du serveur.
\label{tab:published-distances}

Nous sommes moins bons sur les deux distances pour les trois tissus. La MHD de la SB
est notamment beaucoup plus élevée. Les agrégats ne permettent pas d'attribuer cet écart
à une cause précise : des erreurs éloignées de la surface sont une piste à inspecter,
mais nous n'avons pas la vérité terrain du test pour les localiser.

## Temps de calcul et mémoire

Le budget mesuré du modèle de base à 456 paramètres est de 44,5 s pour extraire les
descripteurs d'un sujet, 63,3 s pour entraîner un pli et 1,3 s pour la prédiction une fois
les descripteurs disponibles. Le pic mémoire atteint 3,3 Go et le modèle enregistré 2,5 ko.
**Ces chiffres ne sont pas ceux de la chaîne à auto-contexte soumise.**

Pour la soumission à 939 paramètres, le journal indique 320,1 s d'entraînement final
et 86,7 s par sujet de test en moyenne. Le pic mémoire et la taille du fichier modèle
de cette chaîne n'ont pas été enregistrés. Le budget complet reste donc partiellement
documenté. Les mesures détaillées disponibles figurent dans `report/assets/frugality.md` ;
les machines diffèrent selon les essais et les temps ne se comparent pas tous directement.

La quantification à 64 niveaux n'apporte pas l'économie attendue dans les mesures
disponibles : 87,8 s d'extraction contre 83,1 s à 256 niveaux, avec la même mémoire
du bloc morphologique, 192 Mo. Nous n'en tirons pas une loi sur la vitesse, mais nous
n'avons pas de raison expérimentale de retenir cette variante.

## Exemples qualitatifs

@@FIG5@@

La figure montre le meilleur et le moins bon sujet du leave-one-out de l'auto-contexte :
le sujet 8 obtient 0,8506 et le sujet 2 obtient 0,8215. La coupe est choisie avec la même
règle pour les deux : celle qui contient le plus de voxels du masque.
Les erreurs visibles concernent notamment les frontières entre SG et SB. Nous ne
disposons pas des annotations du test officiel pour produire les mêmes cartes d'erreur
sur les sujets 13 et 20.

# Discussion {#sec:discussion}

**Ce que nous retenons.** Ajouter de l'information autour du voxel améliore notre
classifieur. Nous le voyons avec les descripteurs morphologiques, la remontée de branche
et l'auto-contexte. Cela soutient notre choix de départ, sans démontrer que le contexte
est la seule explication possible. Le test officiel donne un résultat proche de celui
du leave-one-out, mais reste nettement en dessous des références publiées.

**L'auto-dualité ne donne pas le gain de Dice attendu.** À attributs comparables, l'arbre
des formes utilise 52 colonnes morphologiques contre 104 pour les deux arbres séparés.
Le total passe de 187 à 135 colonnes, soit 564 à 408 paramètres. En revanche, son Dice
interne est inférieur de 0,0037 ; la p-valeur corrigée vaut 0,322. Nous n'avons donc pas
mis en évidence d'amélioration de qualité, et l'absence de différence significative
ne prouve pas non plus l'équivalence des deux méthodes. Nous retenons surtout la réduction
de taille. Une explication possible est que notre classifieur exploite mal la structure
supplémentaire, mais nous ne l'avons pas testée.

**Le post-traitement illustre une mauvaise hypothèse de départ.** Nous avions voulu
empêcher tout contact entre SB et LCR. Cette règle est trop générale : elle ne convient
pas aux régions ventriculaires. La baisse mesurée justifie de la retirer. Une version
limitée à certaines régions aurait demandé une nouvelle expérience que nous n'avons
pas menée. Le lissage et le nettoyage, de leur côté, ne donnent pas de bénéfice global
dans nos mesures de Dice et de distances ; nous ne les avons pas soumis.

**La frugalité a un coût de calcul.** Le modèle mémorise peu de coefficients, mais les
descripteurs sont nombreux et parfois coûteux à extraire. Les quelques kilo-octets du
classifieur de base ne décrivent pas la mémoire nécessaire pour traiter un volume entier.
L'intérêt du projet porte d'abord sur le nombre de paramètres appris, pas sur une
supériorité démontrée en vitesse, en énergie ou en mémoire de travail.

**Limites.** Nous avons dix sujets d'entraînement, treize sujets de test et une seule
soumission. Les écarts-types décrivent la variabilité entre sujets ; ils ne mesurent pas
la variabilité entre plusieurs réentraînements de notre méthode. Le choix final parmi
plusieurs configurations utilise les mêmes dix sujets internes : le leave-one-out sert
donc aussi à la sélection, et peut favoriser le modèle retenu. Le test séparé est utile
pour cette raison. Il reste issu du même challenge, sans validation sur un autre centre.

Le temps du hackathon a aussi limité l'exploration. Nous n'avons pas entraîné de réseau
concurrent dans les mêmes conditions, ni recherché systématiquement les meilleurs
hyperparamètres. Les comparaisons publiées servent de repères. Enfin, le classifieur
reste une combinaison assez simple de descripteurs calculés à la main : cela peut limiter
sa capacité à retrouver les frontières les plus ambiguës.

Avec plus de temps, nous commencerions par inspecter les erreurs de surface et tester un
nettoyage mieux ciblé. Nous mesurerions ensuite le temps et la mémoire de toute la chaîne
à auto-contexte de façon reproductible. Ajouter un étage pourrait aussi être essayé,
mais son gain n'est pas acquis.

# Conclusion

Nous avons construit une chaîne de segmentation à **939 paramètres appris**, avec un
Dice moyen de **0,8399 en leave-one-out** et de **0,8445 sur le test officiel** iSeg-2017.
Elle combine des descripteurs calculés sur chaque sujet et deux régressions logistiques
reliées par de l'auto-contexte.

Le résultat officiel atteint 91,0 % du Dice de la référence MSL\_SKKU, avec beaucoup
moins de paramètres que le compte de réseau publié. Il reste inférieur en Dice, ASD
et MHD. L'apport du projet est ce compromis, pas un nouveau meilleur score du challenge.

Le hackathon nous a surtout permis de vérifier quelles idées apportaient quelque chose :
le contexte améliore nos essais, l'auto-dualité réduit la taille sans gain de Dice démontré,
et le post-traitement testé n'est pas retenu. La suite serait de mieux comprendre les
erreurs de contour et de compléter les mesures de coût avant de complexifier le modèle.
'''

ablation = old[old.index('| configuration | param. | LCR'):old.index('## Le score officiel')].strip()
ablation = ablation[:ablation.index(': Ablation')] + ': Dice en leave-one-out sur les dix sujets annotés. Les écarts-types et les distances\nsont disponibles dans `report/assets/ablation.md` et `distances.md`. \\label{tab:ablation}\n'
test = old[old.index('| tissu | Dice | ASD'):old.index('**Le test ne tombe')].strip()
captions = [
    r'Phase isointense sur le sujet 3 : T1, T2, référence et histogrammes SG/SB. Le recouvrement est la somme des minimums des fréquences des deux histogrammes, sur 256 classes : 0 indique des distributions disjointes, 1 des distributions identiques.',
    r'Construction des 151 descripteurs et classifieur de base. La soumission ajoute un second étage d’auto-contexte, décrit en section~3.4.',
    r'Arbre des formes sur une image de synthèse. La branche du voxel $p$ relie les régions emboîtées. Les lignes horizontales indiquent les seuils utilisés pour sélectionner des ancêtres.',
    r'Compromis paramètres--Dice. Le front relié et le zoom concernent uniquement le leave-one-out. Le point de test officiel est distinct et se compare aux deux références publiées. Les comptes des références sont ceux des réseaux publiés ; celui de MSL\_SKKU ne décrit pas nécessairement son ensemble de modèles.',
    r'Ablation en leave-one-out : Dice et intervalles de confiance à 95 \% à gauche ; écarts appariés à droite. Comparer chaque sujet à lui-même réduit une partie de la variabilité entre sujets.',
    r'Meilleur et moins bon sujet du leave-one-out de l’auto-contexte. Les cartes d’erreur utilisent les annotations disponibles sur ces sujets ; elles ne concernent pas le test officiel.'
]
for i in range(6):
    body = body.replace(f'@@FIG{i}@@', figure(i, captions[i]))
body = body.replace('@@ABLATION@@', ablation).replace('@@TEST@@', test)
p.write_text('---'+header+'---\n'+body, encoding='utf-8')
